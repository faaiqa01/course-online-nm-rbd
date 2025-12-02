# Midtrans Service Layer
import midtransclient
from flask import current_app
import json
from datetime import datetime

class MidtransService:
    """Service layer untuk handle Midtrans API"""
    
    @staticmethod
    def get_snap_client():
        """Initialize Midtrans Snap client"""
        snap = midtransclient.Snap(
            is_production=current_app.config.get('MIDTRANS_IS_PRODUCTION', False),
            server_key=current_app.config.get('MIDTRANS_SERVER_KEY', ''),
            client_key=current_app.config.get('MIDTRANS_CLIENT_KEY', '')
        )
        return snap
    
    @staticmethod
    def create_transaction(order_id, user, course=None, custom_item_details=None, gross_amount=None, custom_field1=None):
        """
        Create Midtrans transaction
        
        Args:
            order_id: Unique order ID
            user: User object
            course: Course object (optional if custom_item_details provided)
            custom_item_details: List of item dicts (optional, for cart checkout)
            gross_amount: Total amount (optional, for cart checkout)
            custom_field1: Optional custom field (e.g. for storing course IDs)
            
        Returns:
            dict: Snap transaction response with token
        """
        snap = MidtransService.get_snap_client()
        
        # Determine gross amount
        if gross_amount is not None:
            total_amount = int(gross_amount)
        elif course is not None:
            total_amount = int(course.price)
        else:
            raise ValueError("Either course or gross_amount must be provided")
        
        # Transaction details
        transaction_details = {
            "order_id": order_id,
            "gross_amount": total_amount
        }
        
        # Item details
        if custom_item_details:
            item_details = custom_item_details
        elif course:
            item_details = [{
                "id": str(course.id),
                "price": int(course.price),
                "quantity": 1,
                "name": course.title[:50]  # Limit to 50 chars
            }]
        else:
            raise ValueError("Either course or custom_item_details must be provided")
        
        # Customer details
        customer_details = {
            "first_name": user.name[:50],  # Limit to 50 chars
            "email": user.email,
        }
        
        # Transaction parameter
        transaction = {
            "transaction_details": transaction_details,
            "item_details": item_details,
            "customer_details": customer_details
        }
        
        if custom_field1:
            transaction["custom_field1"] = custom_field1
        
        # Create Snap transaction
        snap_transaction = snap.create_transaction(transaction)
        
        return snap_transaction
    
    @staticmethod
    def verify_notification(notification_data):
        """
        Verify notification from Midtrans
        
        Args:
            notification_data: dict dari Midtrans notification
            
        Returns:
            dict: Verified transaction data
        """
        snap = MidtransService.get_snap_client()
        
        # Get status from Midtrans API
        status_response = snap.transactions.notification(notification_data)
        
        order_id = status_response.get('order_id')
        transaction_status = status_response.get('transaction_status')
        fraud_status = status_response.get('fraud_status', 'accept')
        
        return {
            'order_id': order_id,
            'transaction_status': transaction_status,
            'fraud_status': fraud_status,
            'payment_type': status_response.get('payment_type'),
            'transaction_time': status_response.get('transaction_time'),
            'settlement_time': status_response.get('settlement_time'),
            'custom_field1': status_response.get('custom_field1'),
            'raw_data': json.dumps(status_response)
        }
