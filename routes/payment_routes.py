# Payment Routes untuk Midtrans Integration
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
import uuid
from datetime import datetime, timedelta
import json

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')

@payment_bp.route('/checkout/<int:course_id>')
@login_required
def checkout(course_id):
    """Halaman checkout course"""
    from app import Course, Enrollment, Payment
    from services.midtrans_service import MidtransService

    db = current_app.extensions['sqlalchemy']

    course = Course.query.get_or_404(course_id)

    if not course.is_premium:
        flash('Course ini gratis! Anda bisa langsung mendaftar.', 'info')
        return redirect(url_for('course_detail', course_id=course_id))

    existing_enrollment = db.session.query(Enrollment).filter_by(
        user_id=current_user.id,
        course_id=course_id
    ).first()

    if existing_enrollment:
        flash('Anda sudah terdaftar di course ini!', 'warning')
        return redirect(url_for('course_detail', course_id=course_id))

    return render_template(
        'payment/checkout.html',
        course=course,
        midtrans_client_key=current_app.config.get('MIDTRANS_CLIENT_KEY')
    )

@payment_bp.route('/create-transaction/<int:course_id>', methods=['POST'])
@login_required
def create_transaction(course_id):
    """Create Midtrans transaction"""
    from app import Course, Payment
    from services.midtrans_service import MidtransService

    db = current_app.extensions['sqlalchemy']

    try:
        course = Course.query.get_or_404(course_id)

        if not course.is_premium or course.price <= 0:
            return jsonify({
                'success': False,
                'message': 'Course ini tidak memerlukan pembayaran'
            }), 400

        order_id = f"ORDER-{current_user.id}-{course_id}-{uuid.uuid4().hex[:8].upper()}"

        payment = Payment(
            order_id=order_id,
            user_id=current_user.id,
            course_id=course_id,
            gross_amount=course.price,
            transaction_status='pending'
        )
        db.session.add(payment)
        db.session.commit()

        # compute expiry_time and save into payment_data so invoice can show countdown
        expiry_minutes = current_app.config.get('MIDTRANS_PAYMENT_EXPIRE_MINUTES', 1440)
        expiry_time = (datetime.utcnow() + timedelta(minutes=expiry_minutes)).isoformat()
        try:
            import json as _json
            payment.payment_data = _json.dumps({'expiry_time': expiry_time})
            db.session.commit()
        except Exception:
            db.session.rollback()

        snap_transaction = MidtransService.create_transaction(
            order_id=order_id,
            user=current_user,
            course=course
        )

        return jsonify({
            'success': True,
            'snap_token': snap_transaction['token'],
            'order_id': order_id,
            'expiry_time': expiry_time
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error creating transaction: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500

@payment_bp.route('/notification', methods=['POST'])
def notification_handler():
    """Handle Midtrans payment notification (webhook)"""
    from app import Enrollment, Payment
    from services.midtrans_service import MidtransService

    db = current_app.extensions['sqlalchemy']

    try:
        notification_data = request.get_json()

        if not notification_data:
            notification_data = request.form.to_dict()

        current_app.logger.info(f'Received Midtrans notification: {notification_data}')

        verified_data = MidtransService.verify_notification(notification_data)

        payment = db.session.query(Payment).filter_by(order_id=verified_data['order_id']).first()

        if not payment:
            current_app.logger.error(f'Payment not found for order_id: {verified_data["order_id"]}')
            return jsonify({'message': 'Payment not found'}), 404

        payment.transaction_status = verified_data['transaction_status']
        payment.payment_type = verified_data['payment_type']
        payment.payment_data = verified_data['raw_data']

        if verified_data.get('transaction_time'):
            try:
                payment.transaction_time = datetime.fromisoformat(
                    verified_data['transaction_time'].replace('Z', '+00:00')
                )
            except Exception:
                payment.transaction_time = datetime.utcnow()

        if verified_data['transaction_status'] == 'capture':
            if verified_data['fraud_status'] == 'accept':
                payment.transaction_status = 'settlement'
                _enroll_user_to_course(payment, verified_data.get('custom_field1'))

        elif verified_data['transaction_status'] == 'settlement':
            _enroll_user_to_course(payment, verified_data.get('custom_field1'))

        elif verified_data['transaction_status'] in ['cancel', 'deny', 'expire']:
            payment.transaction_status = verified_data['transaction_status']

        db.session.commit()

        current_app.logger.info(f'Payment {payment.order_id} updated to status: {payment.transaction_status}')

        return jsonify({'message': 'Notification processed'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error processing notification: {str(e)}')
        return jsonify({'message': str(e)}), 500

def _enroll_user_to_course(payment, custom_field1=None):
    """Helper: Enroll user to course(s) after successful payment"""
    from app import Enrollment, CartItem

    db = current_app.extensions['sqlalchemy']

    course_ids = [payment.course_id]
    if custom_field1:
        try:
            course_ids = [int(cid) for cid in custom_field1.split(',') if cid.strip()]
        except ValueError:
            current_app.logger.error(f"Invalid custom_field1 format: {custom_field1}")

    for cid in course_ids:
        existing = db.session.query(Enrollment).filter_by(
            user_id=payment.user_id,
            course_id=cid
        ).first()

        if not existing:
            enrollment = Enrollment(
                user_id=payment.user_id,
                course_id=cid,
                unlocked=True
            )
            db.session.add(enrollment)
            current_app.logger.info(f'User {payment.user_id} enrolled to course {cid}')
        elif not existing.unlocked:
            existing.unlocked = True
            current_app.logger.info(f'User {payment.user_id} course {cid} unlocked')

    if custom_field1 or payment.order_id.startswith('CART-'):
        try:
            db.session.query(CartItem).filter_by(user_id=payment.user_id).delete()
            current_app.logger.info(f'Cart cleared for user {payment.user_id}')
        except Exception as e:
            current_app.logger.error(f'Error clearing cart: {str(e)}')

@payment_bp.route('/success')
@login_required
def payment_success():
    """Payment success page"""
    from app import Payment
    from app import Course

    db = current_app.extensions['sqlalchemy']

    order_id = request.args.get('order_id')
    payment = db.session.query(Payment).filter_by(order_id=order_id).first()

    if not payment:
        flash('Pembayaran tidak ditemukan', 'error')
        return redirect(url_for('index'))

    # If this was a cart checkout, try to populate cart_courses for display in invoice
    try:
        if payment.order_id.startswith('CART-') and payment.payment_data:
            import json
            data = json.loads(payment.payment_data) if isinstance(payment.payment_data, str) else payment.payment_data
            course_ids = []
            if data.get('custom_field1'):
                course_ids = [int(cid) for cid in data.get('custom_field1', '').split(',') if cid.strip()]
            # If we have titles already saved in payment_data, keep them too
            courses = db.session.query(Course).filter(Course.id.in_(course_ids)).all() if course_ids else []
            payment.cart_courses = courses
    except Exception as e:
        current_app.logger.error(f'Error preparing invoice courses: {str(e)}')

    return render_template('payment/success.html', payment=payment)

@payment_bp.route('/history')
@login_required
def payment_history():
    """Payment history page"""
    from app import Payment, Course
    import json

    db = current_app.extensions['sqlalchemy']

    payments = db.session.query(Payment).filter_by(user_id=current_user.id).order_by(
        Payment.created_at.desc()
    ).all()

    # Parse payment_data for cart payments to get course names
    for payment in payments:
        if payment.order_id.startswith('CART-') and payment.payment_data:
            try:
                data = json.loads(payment.payment_data) if isinstance(payment.payment_data, str) else payment.payment_data
                custom_field1 = data.get('custom_field1', '')
                if custom_field1:
                    course_ids = [int(cid) for cid in custom_field1.split(',') if cid.strip()]
                    courses = db.session.query(Course).filter(Course.id.in_(course_ids)).all()
                    payment.cart_courses = courses
                    payment.course_count = len(courses)
                else:
                    payment.cart_courses = []
                    payment.course_count = 0
            except Exception as e:
                current_app.logger.error(f'Error parsing cart payment data: {str(e)}')
                payment.cart_courses = []
                payment.course_count = 0
        else:
            payment.cart_courses = []
            payment.course_count = 1

    return render_template('payment/payment_history.html', payments=payments)


@payment_bp.route('/invoice/<order_id>')
@login_required
def payment_invoice(order_id):
    """Render invoice-like page for order; allow retry when pending"""
    from app import Payment, Course

    db = current_app.extensions['sqlalchemy']

    payment = db.session.query(Payment).filter_by(order_id=order_id, user_id=current_user.id).first()
    if not payment:
        flash('Pembayaran tidak ditemukan', 'error')
        return redirect(url_for('payment.payment_history'))

    # populate cart courses if cart order
    try:
        if payment.order_id.startswith('CART-') and payment.payment_data:
            import json
            data = json.loads(payment.payment_data) if isinstance(payment.payment_data, str) else payment.payment_data
            course_ids = []
            if data.get('custom_field1'):
                course_ids = [int(cid) for cid in data.get('custom_field1', '').split(',') if cid.strip()]
            courses = db.session.query(Course).filter(Course.id.in_(course_ids)).all() if course_ids else []
            payment.cart_courses = courses
            # expose expiry_time for template countdown
            payment.expiry_time = data.get('expiry_time')
    except Exception:
        payment.cart_courses = []
        payment.expiry_time = None

    # If expiry_time not present yet, try to read from payment.payment_data for single-course payments too
    try:
        if not getattr(payment, 'expiry_time', None) and payment.payment_data:
            import json as _json
            pdata = _json.loads(payment.payment_data) if isinstance(payment.payment_data, str) else payment.payment_data
            payment.expiry_time = pdata.get('expiry_time') if pdata else None
    except Exception:
        payment.expiry_time = getattr(payment, 'expiry_time', None)

    # Fallback: if still no expiry_time, compute from created_at using config value
    if not getattr(payment, 'expiry_time', None):
        try:
            expiry_minutes = current_app.config.get('MIDTRANS_PAYMENT_EXPIRE_MINUTES', 1440)
            if getattr(payment, 'created_at', None):
                expiry_dt = payment.created_at + timedelta(minutes=expiry_minutes)
                # store as ISO string
                payment.expiry_time = expiry_dt.isoformat()
            else:
                payment.expiry_time = None
        except Exception:
            payment.expiry_time = None

    midtrans_client_key = current_app.config.get('MIDTRANS_CLIENT_KEY')
    # Ensure we pass a single expiry ISO string to the template (non-destructive)
    expiry_iso = None
    try:
        expiry_iso = payment.expiry_time if getattr(payment, 'expiry_time', None) else None
        if not expiry_iso and getattr(payment, 'created_at', None):
            expiry_minutes = current_app.config.get('MIDTRANS_PAYMENT_EXPIRE_MINUTES', 1440)
            expiry_iso = (payment.created_at + timedelta(minutes=expiry_minutes)).isoformat()
    except Exception:
        expiry_iso = None

    return render_template('payment/invoice.html', payment=payment, midtrans_client_key=midtrans_client_key, expiry_iso=expiry_iso)


@payment_bp.route('/retry/<order_id>', methods=['POST'])
@login_required
def retry_payment(order_id):
    """Create a Snap transaction again for an existing pending payment"""
    from app import Payment
    from services.midtrans_service import MidtransService

    db = current_app.extensions['sqlalchemy']

    payment = db.session.query(Payment).filter_by(order_id=order_id, user_id=current_user.id).first()
    if not payment:
        return jsonify({'success': False, 'message': 'Payment not found'}), 404

    if payment.transaction_status not in ['pending', 'expire']:
        return jsonify({'success': False, 'message': 'Payment is not retryable'}), 400

    try:
        # Build item details and custom_field1 from stored payment_data if present
        item_details = []
        custom_field1 = ''
        try:
            import json
            pdata = json.loads(payment.payment_data) if isinstance(payment.payment_data, str) else payment.payment_data
            if pdata and pdata.get('custom_field1'):
                custom_field1 = pdata.get('custom_field1')
        except Exception:
            custom_field1 = ''

        # If this is a cart (custom_field1 present), build item details by querying Course
        if custom_field1:
            try:
                from app import Course
                course_ids = [int(cid) for cid in custom_field1.split(',') if cid.strip()]
                if course_ids:
                    courses = db.session.query(Course).filter(Course.id.in_(course_ids)).all()
                    for course in courses:
                        item_details.append({
                            'id': f'course-{course.id}',
                            'price': int(course.price or 0),
                            'quantity': 1,
                            'name': course.title[:50]
                        })
            except Exception as e:
                current_app.logger.error(f'Error building item details from custom_field1: {str(e)}')

        # If single course record exists and we don't have item details yet, use that as item
        if not item_details and getattr(payment, 'course_id', None):
            try:
                from app import Course
                course = db.session.query(Course).get(payment.course_id)
                if course:
                    item_details = [{
                        'id': f'course-{course.id}',
                        'price': int(course.price or 0),
                        'quantity': 1,
                        'name': course.title[:50]
                    }]
            except Exception as e:
                current_app.logger.error(f'Error building single-course item detail: {str(e)}')

        # Prefer creating a new order id for retry attempts to avoid duplicate-order issues
        new_order_id = f"{payment.order_id}-RETRY-{uuid.uuid4().hex[:8].upper()}"

        # Create a new Payment record so the webhook from Midtrans maps to this retry order
        from app import Payment as PaymentModel
        new_payment = PaymentModel(
            order_id=new_order_id,
            user_id=payment.user_id,
            course_id=payment.course_id,
            gross_amount=payment.gross_amount,
            transaction_status='pending',
            payment_data=payment.payment_data
        )
        db.session.add(new_payment)
        db.session.commit()

        # compute and store expiry_time for the new retry payment
        expiry_minutes = current_app.config.get('MIDTRANS_PAYMENT_EXPIRE_MINUTES', 1440)
        expiry_time = (datetime.utcnow() + timedelta(minutes=expiry_minutes)).isoformat()
        try:
            import json as _json
            pdata = _json.loads(new_payment.payment_data) if isinstance(new_payment.payment_data, str) and new_payment.payment_data else {}
            pdata['expiry_time'] = expiry_time
            new_payment.payment_data = _json.dumps(pdata)
            db.session.commit()
        except Exception:
            db.session.rollback()

        snap = MidtransService.create_transaction(
            order_id=new_order_id,
            user=current_user,
            course=None,
            custom_item_details=item_details if item_details else None,
            gross_amount=float(payment.gross_amount),
            custom_field1=custom_field1 if custom_field1 else None
        )

        # return snap token, new order id and expiry_time
        return jsonify({'success': True, 'snap_token': snap['token'], 'order_id': new_order_id, 'expiry_time': expiry_time})

    except Exception as e:
        current_app.logger.error(f'Error retrying payment {order_id}: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@payment_bp.route('/check-status/<order_id>', methods=['POST'])
@login_required
def check_status(order_id):
    """Manually check payment status from Midtrans"""
    from app import Payment
    from services.midtrans_service import MidtransService

    db = current_app.extensions['sqlalchemy']

    try:
        payment = db.session.query(Payment).filter_by(order_id=order_id, user_id=current_user.id).first()
        if not payment:
            return jsonify({'success': False, 'message': 'Payment not found'}), 404

        snap = MidtransService.get_snap_client()
        status_response = snap.transactions.status(order_id)

        transaction_status = status_response.get('transaction_status')
        fraud_status = status_response.get('fraud_status', 'accept')
        custom_field1 = status_response.get('custom_field1')

        payment.transaction_status = transaction_status
        payment.payment_type = status_response.get('payment_type')
        payment.payment_data = json.dumps(status_response)

        if status_response.get('transaction_time'):
            try:
                payment.transaction_time = datetime.fromisoformat(
                    status_response['transaction_time'].replace('Z', '+00:00')
                )
            except:
                pass

        if transaction_status == 'capture':
            if fraud_status == 'accept':
                payment.transaction_status = 'settlement'
                _enroll_user_to_course(payment, custom_field1)
        elif transaction_status == 'settlement':
            _enroll_user_to_course(payment, custom_field1)
        elif transaction_status in ['cancel', 'deny', 'expire']:
            payment.transaction_status = transaction_status

        db.session.commit()

        return jsonify({
            'success': True,
            'status': payment.transaction_status,
            'message': f'Status updated to {payment.transaction_status}'
        })

    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        current_app.logger.error(f'Error checking status: {error_msg}')
        
        # Handle 404 - transaction not found in Midtrans
        if '404' in error_msg or "doesn't exist" in error_msg:
            return jsonify({
                'success': False, 
                'message': 'Transaksi tidak ditemukan di Midtrans. Kemungkinan popup dibatalkan sebelum pembayaran diproses.'
            }), 404
        
        return jsonify({'success': False, 'message': error_msg}), 500

@payment_bp.route('/delete/<order_id>', methods=['POST'])
@login_required
def delete_payment(order_id):
    """Delete orphan payment record"""
    from app import Payment

    db = current_app.extensions['sqlalchemy']

    try:
        payment = db.session.query(Payment).filter_by(
            order_id=order_id, 
            user_id=current_user.id
        ).first()
        
        if not payment:
            return jsonify({'success': False, 'message': 'Payment not found'}), 404

        # Only allow deletion of pending/failed payments
        if payment.transaction_status not in ['pending', 'expire', 'cancel', 'deny']:
            return jsonify({
                'success': False, 
                'message': 'Hanya pembayaran pending/gagal yang bisa dihapus'
            }), 400

        db.session.delete(payment)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Payment record berhasil dihapus'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting payment: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500


@payment_bp.route('/mark-failed/<order_id>', methods=['POST'])
@login_required
def mark_failed_payment(order_id):
    """Mark a pending payment as failed/cancelled when user closes payment popup"""
    from app import Payment

    db = current_app.extensions['sqlalchemy']

    try:
        payment = db.session.query(Payment).filter_by(order_id=order_id, user_id=current_user.id).first()
        if not payment:
            return jsonify({'success': False, 'message': 'Payment not found'}), 404

        if payment.transaction_status not in ['pending', 'expire']:
            return jsonify({'success': False, 'message': 'Only pending/expired payments can be marked failed'}), 400

        # update status to cancelled and add a note into payment_data
        payment.transaction_status = 'cancel'
        try:
            import json as _json
            pdata = _json.loads(payment.payment_data) if isinstance(payment.payment_data, str) and payment.payment_data else (payment.payment_data or {})
            pdata['popup_closed'] = True
            pdata['popup_closed_at'] = datetime.utcnow().isoformat()
            payment.payment_data = _json.dumps(pdata)
        except Exception:
            # fallback: write a simple note
            try:
                payment.payment_data = (payment.payment_data or '') + '\npopup_closed'
            except Exception:
                pass

        db.session.commit()
        return jsonify({'success': True, 'message': 'Payment marked as cancelled'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error marking payment failed: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500
