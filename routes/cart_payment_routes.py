# Cart Payment Routes - Midtrans Integration untuk Cart
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
import uuid

cart_payment_bp = Blueprint('cart_payment', __name__, url_prefix='/cart/checkout')

@cart_payment_bp.route('/create-midtrans-transactions', methods=['POST'])
@login_required
def create_midtrans_transactions():
    """Create Midtrans transaction for all cart items"""
    from app import CartItem, Course, Payment
    from services.midtrans_service import MidtransService
    
    db = current_app.extensions['sqlalchemy']
    
    try:
        if current_user.role != 'student':
            return jsonify({'success': False, 'message': 'Fitur keranjang hanya untuk student.'}), 403
        
        # Get cart items
        items = db.session.query(CartItem).filter_by(user_id=current_user.id).all()
        if not items:
            return jsonify({'success': False, 'message': 'Keranjang kosong.'}), 400
        
        # Get courses
        course_ids = [item.course_id for item in items]
        courses = db.session.query(Course).filter(Course.id.in_(course_ids)).all() if course_ids else []
        course_map = {course.id: course for course in courses}
        
        # Calculate total and create single transaction for all items
        total_amount = 0
        course_titles = []
        
        for item in items:
            course = course_map.get(item.course_id)
            if course and course.is_premium:
                total_amount += course.price or 0
                course_titles.append(course.title)
        
        if total_amount == 0:
            return jsonify({'success': False, 'message': 'Tidak ada course premium di keranjang'}), 400
        
        # Generate unique order ID for cart checkout
        order_id = f"CART-{current_user.id}-{uuid.uuid4().hex[:8].upper()}"
        
        # Create payment record untuk first course (as primary)
        first_premium_course = next((course_map.get(item.course_id) for item in items 
                                    if course_map.get(item.course_id) and course_map.get(item.course_id).is_premium), None)
        
        if not first_premium_course:
            return jsonify({'success': False, 'message': 'Tidak ada course premium'}), 400
        
        payment = Payment(
            order_id=order_id,
            user_id=current_user.id,
            course_id=first_premium_course.id,  # Store first course as reference
            gross_amount=total_amount,
            transaction_status='pending'
        )
        db.session.add(payment)
        db.session.commit()
        
        # Create Midtrans transaction with combined items
        item_details = []
        premium_course_ids = []
        for item in items:
            course = course_map.get(item.course_id)
            if course and course.is_premium:
                premium_course_ids.append(str(course.id))
                item_details.append({
                    'id': f'course-{course.id}',
                    'price': int(course.price or 0),
                    'quantity': 1,
                    'name': course.title[:50]  # Midtrans has char limit
                })
        
        # Join course IDs for custom_field1
        custom_field1 = ",".join(premium_course_ids)
        
        # Save course_ids info to payment_data for later display
        import json
        payment.payment_data = json.dumps({
            'custom_field1': custom_field1,
            'course_titles': course_titles
        })
        db.session.commit()
        
        snap_transaction = MidtransService.create_transaction(
            order_id=order_id,
            user=current_user,
            course=None,  # Pass None since it's multiple courses
            custom_item_details=item_details,
            gross_amount=total_amount,
            custom_field1=custom_field1
        )
        
        return jsonify({
            'success': True,
            'snap_token': snap_transaction['token'],
            'order_id': order_id
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error creating cart Midtrans transaction: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500
