# Payment Routes untuk Midtrans Integration
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
import uuid
from datetime import datetime
import json

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')

@payment_bp.route('/checkout/<int:course_id>')
@login_required
def checkout(course_id):
    """Halaman checkout course"""
    # Import hanya model untuk menghindari multiple SQLAlchemy instance
    from app import Course, Enrollment, Payment
    from services.midtrans_service import MidtransService

    db = current_app.extensions['sqlalchemy']

    course = Course.query.get_or_404(course_id)

    # Check if not premium course
    if not course.is_premium:
        flash('Course ini gratis! Anda bisa langsung mendaftar.', 'info')
        return redirect(url_for('course_detail', course_id=course_id))

    # Check if already enrolled
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

        # Validate course is premium
        if not course.is_premium or course.price <= 0:
            return jsonify({
                'success': False,
                'message': 'Course ini tidak memerlukan pembayaran'
            }), 400

        # Generate unique order ID
        order_id = f"ORDER-{current_user.id}-{course_id}-{uuid.uuid4().hex[:8].upper()}"

        # Create payment record
        payment = Payment(
            order_id=order_id,
            user_id=current_user.id,
            course_id=course_id,
            gross_amount=course.price,
            transaction_status='pending'
        )
        db.session.add(payment)
        db.session.commit()

        # Create Midtrans transaction
        snap_transaction = MidtransService.create_transaction(
            order_id=order_id,
            user=current_user,
            course=course
        )

        return jsonify({
            'success': True,
            'snap_token': snap_transaction['token'],
            'order_id': order_id
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

        # Verify notification
        verified_data = MidtransService.verify_notification(notification_data)

        # Find payment record
        payment = db.session.query(Payment).filter_by(order_id=verified_data['order_id']).first()

        if not payment:
            current_app.logger.error(f'Payment not found for order_id: {verified_data["order_id"]}')
            return jsonify({'message': 'Payment not found'}), 404

        # Update payment status
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
# Payment Routes untuk Midtrans Integration
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
import uuid
from datetime import datetime
import json # Added for json.dumps in check_status

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')

@payment_bp.route('/checkout/<int:course_id>')
@login_required
def checkout(course_id):
    """Halaman checkout course"""
    # Import hanya model untuk menghindari multiple SQLAlchemy instance
    from app import Course, Enrollment, Payment
    from services.midtrans_service import MidtransService

    db = current_app.extensions['sqlalchemy']

    course = Course.query.get_or_404(course_id)

    # Check if not premium course
    if not course.is_premium:
        flash('Course ini gratis! Anda bisa langsung mendaftar.', 'info')
        return redirect(url_for('course_detail', course_id=course_id))

    # Check if already enrolled
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

        # Validate course is premium
        if not course.is_premium or course.price <= 0:
            return jsonify({
                'success': False,
                'message': 'Course ini tidak memerlukan pembayaran'
            }), 400

        # Generate unique order ID
        order_id = f"ORDER-{current_user.id}-{course_id}-{uuid.uuid4().hex[:8].upper()}"

        # Create payment record
        payment = Payment(
            order_id=order_id,
            user_id=current_user.id,
            course_id=course_id,
            gross_amount=course.price,
            transaction_status='pending'
        )
        db.session.add(payment)
        db.session.commit()

        # Create Midtrans transaction
        snap_transaction = MidtransService.create_transaction(
            order_id=order_id,
            user=current_user,
            course=course
        )

        return jsonify({
            'success': True,
            'snap_token': snap_transaction['token'],
            'order_id': order_id
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

        # Verify notification
        verified_data = MidtransService.verify_notification(notification_data)

        # Find payment record
        payment = db.session.query(Payment).filter_by(order_id=verified_data['order_id']).first()

        if not payment:
            current_app.logger.error(f'Payment not found for order_id: {verified_data["order_id"]}')
            return jsonify({'message': 'Payment not found'}), 404

        # Update payment status
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

        # Handle payment status
        if verified_data['transaction_status'] == 'capture':
            if verified_data['fraud_status'] == 'accept':
                # Payment success
                payment.transaction_status = 'settlement'
                _enroll_user_to_course(payment, verified_data.get('custom_field1'))

        elif verified_data['transaction_status'] == 'settlement':
            # Payment success
            _enroll_user_to_course(payment, verified_data.get('custom_field1'))

        elif verified_data['transaction_status'] in ['cancel', 'deny', 'expire']:
            # Payment failed
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

    # Determine courses to enroll
    course_ids = [payment.course_id]
    if custom_field1:
        try:
            course_ids = [int(cid) for cid in custom_field1.split(',') if cid.strip()]
        except ValueError:
            current_app.logger.error(f"Invalid custom_field1 format: {custom_field1}")

    for cid in course_ids:
        # Check if already enrolled
        existing = db.session.query(Enrollment).filter_by(
            user_id=payment.user_id,
            course_id=cid
        ).first()

        if not existing:
            enrollment = Enrollment(
                user_id=payment.user_id,
                course_id=cid,
                unlocked=True  # Mark as paid/unlocked
            )
            db.session.add(enrollment)
            current_app.logger.info(f'User {payment.user_id} enrolled to course {cid}')
        elif not existing.unlocked:
            existing.unlocked = True
            current_app.logger.info(f'User {payment.user_id} course {cid} unlocked')

    # Clear cart if this was a cart checkout (indicated by custom_field1 or order_id prefix)
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

    db = current_app.extensions['sqlalchemy']

    order_id = request.args.get('order_id')
    payment = db.session.query(Payment).filter_by(order_id=order_id).first()

    if not payment:
        flash('Pembayaran tidak ditemukan', 'error')
        return redirect(url_for('index'))

    return render_template('payment/success.html', payment=payment)

@payment_bp.route('/history')
@login_required
def payment_history():
    """Payment history page"""
    from app import Payment

    db = current_app.extensions['sqlalchemy']

    payments = db.session.query(Payment).filter_by(user_id=current_user.id).order_by(
        Payment.created_at.desc()
    ).all()

    return render_template('payment/payment_history.html', payments=payments)

@payment_bp.route('/check-status/<order_id>', methods=['POST'])
@login_required
def check_status(order_id):
    """Manually check payment status from Midtrans (useful for localhost)"""
    from app import Payment
    from services.midtrans_service import MidtransService

    db = current_app.extensions['sqlalchemy']

    try:
        payment = db.session.query(Payment).filter_by(order_id=order_id, user_id=current_user.id).first()
        if not payment:
            return jsonify({'success': False, 'message': 'Payment not found'}), 404

        # Get status from Midtrans
        snap = MidtransService.get_snap_client()
        status_response = snap.transactions.status(order_id)

        transaction_status = status_response.get('transaction_status')
        fraud_status = status_response.get('fraud_status', 'accept')
        custom_field1 = status_response.get('custom_field1')

        # Update payment
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

        # Handle success
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
        current_app.logger.error(f'Error checking status: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500
