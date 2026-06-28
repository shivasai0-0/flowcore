import os
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("flowcore.capability_registry")

CAPABILITIES_DATA: Dict[str, Dict[str, Any]] = {
    # CORE CAPABILITIES
    "show_catalog": {
        "module_name": "show_catalog",
        "version": "1.0",
        "category": "Core",
        "description": "Displays the business catalog or main options menu",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "collect_information": {
        "module_name": "collect_information",
        "version": "1.0",
        "category": "Core",
        "description": "Collects generic text input from the customer",
        "inputs": ["str"],
        "outputs": {"collected_text": "str"},
        "required_config": ["prompt_message"],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "collect_contact_details": {
        "module_name": "collect_contact_details",
        "version": "1.0",
        "category": "Core",
        "description": "Collects phone or email from customer",
        "inputs": ["str"],
        "outputs": {"customer.phone": "str", "customer.email": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "collect_address": {
        "module_name": "collect_address",
        "version": "1.0",
        "category": "Core",
        "description": "Collects customer delivery address",
        "inputs": ["str"],
        "outputs": {"customer.address": "str", "logistics.address": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "notify_customer": {
        "module_name": "notify_customer",
        "version": "1.0",
        "category": "Core",
        "description": "Sends customer notification via active channel",
        "inputs": [],
        "outputs": {},
        "required_config": ["notification_provider"],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "collect_feedback": {
        "module_name": "collect_feedback",
        "version": "1.0",
        "category": "Core",
        "description": "Collects feedback or CSAT score",
        "inputs": ["str"],
        "outputs": {"feedback.score": "int", "feedback.text": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["FEEDBACK_SUBMITTED"],
        "events_consumed": []
    },
    "create_order": {
        "module_name": "create_order",
        "version": "1.0",
        "category": "Core",
        "description": "Creates order entry in PLACED state",
        "inputs": [],
        "outputs": {"order.status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["ORDER_CREATED"],
        "events_consumed": []
    },
    "update_order": {
        "module_name": "update_order",
        "version": "1.0",
        "category": "Core",
        "description": "Updates order properties",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["ORDER_UPDATED"],
        "events_consumed": []
    },
    "cancel_order": {
        "module_name": "cancel_order",
        "version": "1.0",
        "category": "Core",
        "description": "Cancels active order",
        "inputs": [],
        "outputs": {"order.status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["ORDER_CANCELLED"],
        "events_consumed": []
    },
    "review_cart": {
        "module_name": "review_cart",
        "version": "1.0",
        "category": "Core",
        "description": "Reviews the current cart contents",
        "inputs": [],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "calculate_total": {
        "module_name": "calculate_total",
        "version": "1.0",
        "category": "Core",
        "description": "Calculates total order pricing",
        "inputs": [],
        "outputs": {"order.total": "float"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "create_booking": {
        "module_name": "create_booking",
        "version": "1.0",
        "category": "Core",
        "description": "Creates scheduling booking",
        "inputs": ["str"],
        "outputs": {"booking.id": "str", "booking.status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["BOOKING_CREATED"],
        "events_consumed": []
    },
    "update_booking": {
        "module_name": "update_booking",
        "version": "1.0",
        "category": "Core",
        "description": "Updates active booking schedule",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "cancel_booking": {
        "module_name": "cancel_booking",
        "version": "1.0",
        "category": "Core",
        "description": "Cancels scheduled booking",
        "inputs": [],
        "outputs": {"booking.status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["BOOKING_CANCELLED"],
        "events_consumed": []
    },
    "reschedule_booking": {
        "module_name": "reschedule_booking",
        "version": "1.0",
        "category": "Core",
        "description": "Reschedules booking time",
        "inputs": ["str"],
        "outputs": {"booking.time": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "create_payment": {
        "module_name": "create_payment",
        "version": "1.0",
        "category": "Core",
        "description": "Creates payment transaction link",
        "inputs": [],
        "outputs": {"payment.payment_url": "str", "payment.transaction_id": "str", "payment.status": "str"},
        "required_config": ["payment_provider"],
        "optional_config": ["allow_cod", "currency"],
        "events_emitted": ["PAYMENT_REQUIRED"],
        "events_consumed": []
    },
    "verify_payment": {
        "module_name": "verify_payment",
        "version": "1.0",
        "category": "Core",
        "description": "Verifies payment status",
        "inputs": ["str"],
        "outputs": {"payment.status": "str"},
        "required_config": ["payment_provider"],
        "optional_config": [],
        "events_emitted": ["PAYMENT_COMPLETED", "PAYMENT_FAILED"],
        "events_consumed": []
    },
    "refund_payment": {
        "module_name": "refund_payment",
        "version": "1.0",
        "category": "Core",
        "description": "Refunds payment transaction",
        "inputs": [],
        "outputs": {"payment.status": "str"},
        "required_config": ["payment_provider"],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "create_delivery": {
        "module_name": "create_delivery",
        "version": "1.0",
        "category": "Core",
        "description": "Creates logistics delivery order",
        "inputs": [],
        "outputs": {"logistics.delivery_id": "str", "logistics.status": "str"},
        "required_config": ["delivery_provider"],
        "optional_config": ["delivery_fee", "max_distance"],
        "events_emitted": ["DELIVERY_CREATED"],
        "events_consumed": []
    },
    "track_delivery": {
        "module_name": "track_delivery",
        "version": "1.0",
        "category": "Core",
        "description": "Tracks delivery status",
        "inputs": [],
        "outputs": {"logistics.status": "str"},
        "required_config": ["delivery_provider"],
        "optional_config": [],
        "events_emitted": ["DELIVERY_COMPLETED"],
        "events_consumed": []
    },
    "cancel_delivery": {
        "module_name": "cancel_delivery",
        "version": "1.0",
        "category": "Core",
        "description": "Cancels delivery order",
        "inputs": [],
        "outputs": {"logistics.status": "str"},
        "required_config": ["delivery_provider"],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "create_support_ticket": {
        "module_name": "create_support_ticket",
        "version": "1.0",
        "category": "Core",
        "description": "Creates a new support ticket",
        "inputs": ["str"],
        "outputs": {"support.ticket_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["SUPPORT_REQUESTED"],
        "events_consumed": []
    },
    "escalate_support": {
        "module_name": "escalate_support",
        "version": "1.0",
        "category": "Core",
        "description": "Escalates support ticket",
        "inputs": [],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["SUPPORT_ESCALATED"],
        "events_consumed": []
    },
    "close_support_ticket": {
        "module_name": "close_support_ticket",
        "version": "1.0",
        "category": "Core",
        "description": "Closes support ticket",
        "inputs": [],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "request_approval": {
        "module_name": "request_approval",
        "version": "1.0",
        "category": "Core",
        "description": "Requests manager approval",
        "inputs": ["str"],
        "outputs": {"approval.status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["APPROVAL_REQUESTED"],
        "events_consumed": []
    },
    "approve_request": {
        "module_name": "approve_request",
        "version": "1.0",
        "category": "Core",
        "description": "Approves approval request",
        "inputs": [],
        "outputs": {"approval.status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["APPROVAL_GRANTED"],
        "events_consumed": []
    },
    "reject_request": {
        "module_name": "reject_request",
        "version": "1.0",
        "category": "Core",
        "description": "Rejects approval request",
        "inputs": [],
        "outputs": {"approval.status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["APPROVAL_REJECTED"],
        "events_consumed": []
    },
    "assign_staff": {
        "module_name": "assign_staff",
        "version": "1.0",
        "category": "Core",
        "description": "Assigns business staff",
        "inputs": [],
        "outputs": {"staff.assigned_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "assign_delivery_partner": {
        "module_name": "assign_delivery_partner",
        "version": "1.0",
        "category": "Core",
        "description": "Assigns delivery rider",
        "inputs": [],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "update_status": {
        "module_name": "update_status",
        "version": "1.0",
        "category": "Core",
        "description": "Updates general workflow status",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "create_customer": {
        "module_name": "create_customer",
        "version": "1.0",
        "category": "Core",
        "description": "Creates customer record",
        "inputs": [],
        "outputs": {"customer.id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["CUSTOMER_CREATED"],
        "events_consumed": []
    },
    "update_customer": {
        "module_name": "update_customer",
        "version": "1.0",
        "category": "Core",
        "description": "Updates customer metadata",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "add_loyalty_points": {
        "module_name": "add_loyalty_points",
        "version": "1.0",
        "category": "Core",
        "description": "Adds points to customer account",
        "inputs": [],
        "outputs": {},
        "required_config": ["points_to_add"],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "redeem_loyalty_points": {
        "module_name": "redeem_loyalty_points",
        "version": "1.0",
        "category": "Core",
        "description": "Redeems customer loyalty points",
        "inputs": [],
        "outputs": {},
        "required_config": ["points_to_redeem"],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "record_event": {
        "module_name": "record_event",
        "version": "1.0",
        "category": "Core",
        "description": "Records analytics event",
        "inputs": ["str"],
        "outputs": {},
        "required_config": ["event_name"],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "record_conversion": {
        "module_name": "record_conversion",
        "version": "1.0",
        "category": "Core",
        "description": "Records business conversion event",
        "inputs": [],
        "outputs": {},
        "required_config": ["conversion_type"],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "record_dropoff": {
        "module_name": "record_dropoff",
        "version": "1.0",
        "category": "Core",
        "description": "Records dropoff metrics",
        "inputs": [],
        "outputs": {},
        "required_config": ["dropoff_stage"],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "create_reminder": {
        "module_name": "create_reminder",
        "version": "1.0",
        "category": "Core",
        "description": "Creates customer session reminder",
        "inputs": [],
        "outputs": {},
        "required_config": ["delay_seconds", "message"],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "schedule_followup": {
        "module_name": "schedule_followup",
        "version": "1.0",
        "category": "Core",
        "description": "Schedules followup turn",
        "inputs": [],
        "outputs": {},
        "required_config": ["delay_seconds"],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "assign_task": {
        "module_name": "assign_task",
        "version": "1.0",
        "category": "Core",
        "description": "Assigns a task to a worker",
        "inputs": [],
        "outputs": {"task.id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["TASK_CREATED"],
        "events_consumed": []
    },
    "generate_report": {
        "module_name": "generate_report",
        "version": "1.0",
        "category": "Core",
        "description": "Generates business reports such as schedules and summaries",
        "inputs": [],
        "outputs": {"report.id": "str"},
        "required_config": ["report_type"],
        "optional_config": [],
        "events_emitted": ["REPORT_GENERATED"],
        "events_consumed": []
    },
    "send_report_whatsapp": {
        "module_name": "send_report_whatsapp",
        "version": "1.0",
        "category": "Core",
        "description": "Sends a report via WhatsApp",
        "inputs": [],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["REPORT_DELIVERED"],
        "events_consumed": []
    },

    # RESTAURANT PACK
    "show_menu": {
        "module_name": "show_menu",
        "version": "1.0",
        "category": "Restaurant",
        "description": "Displays the restaurant catalog menu",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "collect_cart": {
        "module_name": "collect_cart",
        "version": "1.0",
        "category": "Restaurant",
        "description": "Collects food items/quantities into cart",
        "inputs": ["str"],
        "outputs": {"order.items": "list"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },

    # SALON PACK
    "show_services": {
        "module_name": "show_services",
        "version": "1.0",
        "category": "Salon",
        "description": "Displays services catalog",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "select_stylist": {
        "module_name": "select_stylist",
        "version": "1.0",
        "category": "Salon",
        "description": "Selects stylist styling partner",
        "inputs": ["str"],
        "outputs": {"salon.stylist_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "membership_management": {
        "module_name": "membership_management",
        "version": "1.0",
        "category": "Salon",
        "description": "Manages salon membership status",
        "inputs": ["str"],
        "outputs": {"salon.membership_status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },

    # CLINIC PACK
    "show_doctors": {
        "module_name": "show_doctors",
        "version": "1.0",
        "category": "Clinic",
        "description": "Displays clinic doctors catalog",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "create_appointment": {
        "module_name": "create_appointment",
        "version": "1.0",
        "category": "Clinic",
        "description": "Creates doctor appointment schedule",
        "inputs": ["str"],
        "outputs": {"clinic.appointment_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "collect_patient_info": {
        "module_name": "collect_patient_info",
        "version": "1.0",
        "category": "Clinic",
        "description": "Collects patient registration details",
        "inputs": ["str"],
        "outputs": {"clinic.patient_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "prescription_followup": {
        "module_name": "prescription_followup",
        "version": "1.0",
        "category": "Clinic",
        "description": "Sends prescription follow-up reminders",
        "inputs": [],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "appointment_reminders": {
        "module_name": "appointment_reminders",
        "version": "1.0",
        "category": "Clinic",
        "description": "Schedules appointment reminders",
        "inputs": [],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },

    # HOSPITAL PACK
    "department_selection": {
        "module_name": "department_selection",
        "version": "1.0",
        "category": "Hospital",
        "description": "Selects hospital department",
        "inputs": ["str"],
        "outputs": {"hospital.department": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "doctor_assignment": {
        "module_name": "doctor_assignment",
        "version": "1.0",
        "category": "Hospital",
        "description": "Assigns hospital doctor",
        "inputs": ["str"],
        "outputs": {"hospital.doctor_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "patient_registration": {
        "module_name": "patient_registration",
        "version": "1.0",
        "category": "Hospital",
        "description": "Registers patient in database",
        "inputs": ["str"],
        "outputs": {"hospital.patient_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "appointment_management": {
        "module_name": "appointment_management",
        "version": "1.0",
        "category": "Hospital",
        "description": "Manages patient appointments",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "admission_request": {
        "module_name": "admission_request",
        "version": "1.0",
        "category": "Hospital",
        "description": "Creates bed admission request",
        "inputs": ["str"],
        "outputs": {"hospital.admission_status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "discharge_management": {
        "module_name": "discharge_management",
        "version": "1.0",
        "category": "Hospital",
        "description": "Processes patient discharge request",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "lab_test_booking": {
        "module_name": "lab_test_booking",
        "version": "1.0",
        "category": "Hospital",
        "description": "Books clinical laboratory test",
        "inputs": ["str"],
        "outputs": {"hospital.lab_booking_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "report_collection": {
        "module_name": "report_collection",
        "version": "1.0",
        "category": "Hospital",
        "description": "Retrieves medical test report pdf",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "emergency_escalation": {
        "module_name": "emergency_escalation",
        "version": "1.0",
        "category": "Hospital",
        "description": "Escalates patient emergency status",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "billing_management": {
        "module_name": "billing_management",
        "version": "1.0",
        "category": "Hospital",
        "description": "Manages hospital billing and invoices",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },

    # GYM PACK
    "membership_signup": {
        "module_name": "membership_signup",
        "version": "1.0",
        "category": "Gym",
        "description": "Gym membership signup",
        "inputs": ["str"],
        "outputs": {"gym.membership_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "membership_renewal": {
        "module_name": "membership_renewal",
        "version": "1.0",
        "category": "Gym",
        "description": "Renews membership status",
        "inputs": [],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "trainer_booking": {
        "module_name": "trainer_booking",
        "version": "1.0",
        "category": "Gym",
        "description": "Books a personal trainer",
        "inputs": ["str"],
        "outputs": {"gym.trainer_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "class_booking": {
        "module_name": "class_booking",
        "version": "1.0",
        "category": "Gym",
        "description": "Books gym class schedule",
        "inputs": ["str"],
        "outputs": {"gym.class_booking_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "attendance_tracking": {
        "module_name": "attendance_tracking",
        "version": "1.0",
        "category": "Gym",
        "description": "Tracks gym member attendance",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },

    # ECOMMERCE PACK
    "show_products": {
        "module_name": "show_products",
        "version": "1.0",
        "category": "Ecommerce",
        "description": "Displays product catalog listing",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "manage_cart": {
        "module_name": "manage_cart",
        "version": "1.0",
        "category": "Ecommerce",
        "description": "Adds or removes items from cart",
        "inputs": ["str"],
        "outputs": {"order.items": "list"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "checkout": {
        "module_name": "checkout",
        "version": "1.0",
        "category": "Ecommerce",
        "description": "Starts checkout process",
        "inputs": [],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "shipping": {
        "module_name": "shipping",
        "version": "1.0",
        "category": "Ecommerce",
        "description": "Sets shipping details",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "returns": {
        "module_name": "returns",
        "version": "1.0",
        "category": "Ecommerce",
        "description": "Processes return request",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "order_tracking": {
        "module_name": "order_tracking",
        "version": "1.0",
        "category": "Ecommerce",
        "description": "Tracks order status",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },

    # REAL ESTATE PACK
    "lead_capture": {
        "module_name": "lead_capture",
        "version": "1.0",
        "category": "RealEstate",
        "description": "Captures real estate leads details",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "property_listing": {
        "module_name": "property_listing",
        "version": "1.0",
        "category": "RealEstate",
        "description": "Displays property listings",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "property_visit_booking": {
        "module_name": "property_visit_booking",
        "version": "1.0",
        "category": "RealEstate",
        "description": "Books site property visit",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "broker_assignment": {
        "module_name": "broker_assignment",
        "version": "1.0",
        "category": "RealEstate",
        "description": "Assigns real estate broker",
        "inputs": ["str"],
        "outputs": {"realestate.broker_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "followup_management": {
        "module_name": "followup_management",
        "version": "1.0",
        "category": "RealEstate",
        "description": "Manages lead follow-ups",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },

    # EDUCATION PACK
    "course_catalog": {
        "module_name": "course_catalog",
        "version": "1.0",
        "category": "Education",
        "description": "Displays courses catalog",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "admission_enquiry": {
        "module_name": "admission_enquiry",
        "version": "1.0",
        "category": "Education",
        "description": "Handles student admission enquiries",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "fee_collection": {
        "module_name": "fee_collection",
        "version": "1.0",
        "category": "Education",
        "description": "Processes fee payment transactions",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "attendance_notifications": {
        "module_name": "attendance_notifications",
        "version": "1.0",
        "category": "Education",
        "description": "Sends student attendance notifications",
        "inputs": [],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "student_support": {
        "module_name": "student_support",
        "version": "1.0",
        "category": "Education",
        "description": "Handles student academic support queries",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },

    # SERVICE BUSINESS PACK
    "service_request": {
        "module_name": "service_request",
        "version": "1.0",
        "category": "ServiceBusiness",
        "description": "Initiates service job request",
        "inputs": ["str"],
        "outputs": {"service.job_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "estimate_generation": {
        "module_name": "estimate_generation",
        "version": "1.0",
        "category": "ServiceBusiness",
        "description": "Generates job pricing estimate",
        "inputs": [],
        "outputs": {"service.estimate_total": "float"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "technician_assignment": {
        "module_name": "technician_assignment",
        "version": "1.0",
        "category": "ServiceBusiness",
        "description": "Assigns field service technician",
        "inputs": [],
        "outputs": {"service.technician_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "visit_scheduling": {
        "module_name": "visit_scheduling",
        "version": "1.0",
        "category": "ServiceBusiness",
        "description": "Schedules technician visit slot",
        "inputs": ["str"],
        "outputs": {"service.scheduled_time": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "work_completion": {
        "module_name": "work_completion",
        "version": "1.0",
        "category": "ServiceBusiness",
        "description": "Processes technician job completion report",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },

    # PHARMACY PACK
    "medicine_catalog": {
        "module_name": "medicine_catalog",
        "version": "1.0",
        "category": "Pharmacy",
        "description": "Displays list of catalog medicines",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "prescription_upload": {
        "module_name": "prescription_upload",
        "version": "1.0",
        "category": "Pharmacy",
        "description": "Handles medicine prescription upload/parsing",
        "inputs": ["str"],
        "outputs": {"pharmacy.prescription_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "medicine_order": {
        "module_name": "medicine_order",
        "version": "1.0",
        "category": "Pharmacy",
        "description": "Places medicine order request",
        "inputs": [],
        "outputs": {"order.status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["ORDER_CREATED"],
        "events_consumed": []
    },
    "medicine_delivery": {
        "module_name": "medicine_delivery",
        "version": "1.0",
        "category": "Pharmacy",
        "description": "Schedules pharmacy medicine delivery",
        "inputs": [],
        "outputs": {"logistics.delivery_id": "str", "logistics.status": "str"},
        "required_config": ["delivery_provider"],
        "optional_config": [],
        "events_emitted": ["DELIVERY_CREATED"],
        "events_consumed": []
    },

    # HOTEL PACK
    "room_booking": {
        "module_name": "room_booking",
        "version": "1.0",
        "category": "Hotel",
        "description": "Processes room reservation booking",
        "inputs": ["str"],
        "outputs": {"booking.id": "str", "booking.status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["BOOKING_CREATED"],
        "events_consumed": []
    },
    "room_upgrade": {
        "module_name": "room_upgrade",
        "version": "1.0",
        "category": "Hotel",
        "description": "Handles room category upgrade request",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "check_in": {
        "module_name": "check_in",
        "version": "1.0",
        "category": "Hotel",
        "description": "Handles guest check-in processing",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "check_out": {
        "module_name": "check_out",
        "version": "1.0",
        "category": "Hotel",
        "description": "Processes guest check-out and bills",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },

    # TRAVEL PACK
    "trip_booking": {
        "module_name": "trip_booking",
        "version": "1.0",
        "category": "Travel",
        "description": "Books customized vacation package trips",
        "inputs": ["str"],
        "outputs": {"booking.id": "str", "booking.status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["BOOKING_CREATED"],
        "events_consumed": []
    },
    "ticket_booking": {
        "module_name": "ticket_booking",
        "version": "1.0",
        "category": "Travel",
        "description": "Books flight, bus, or train tickets",
        "inputs": ["str"],
        "outputs": {"travel.ticket_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "itinerary_management": {
        "module_name": "itinerary_management",
        "version": "1.0",
        "category": "Travel",
        "description": "Displays and updates trip itineraries",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "confirm_order": {
        "module_name": "confirm_order",
        "version": "1.0",
        "category": "Restaurant",
        "description": "Confirms restaurant order placement",
        "inputs": [],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "select_department": {
        "module_name": "select_department",
        "version": "1.0",
        "category": "Hospital",
        "description": "Selects hospital department",
        "inputs": ["str"],
        "outputs": {"hospital.department": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "select_doctor": {
        "module_name": "select_doctor",
        "version": "1.0",
        "category": "Hospital",
        "description": "Assigns hospital doctor",
        "inputs": ["str"],
        "outputs": {"hospital.doctor_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "select_slot": {
        "module_name": "select_slot",
        "version": "1.0",
        "category": "Hospital",
        "description": "Selects appointment slot",
        "inputs": ["str"],
        "outputs": {"hospital.slot_time": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "book_appointment": {
        "module_name": "book_appointment",
        "version": "1.0",
        "category": "Hospital",
        "description": "Creates doctor appointment schedule",
        "inputs": [],
        "outputs": {"booking.id": "str", "booking.status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["BOOKING_CREATED"],
        "events_consumed": []
    },
    "approve_appointment": {
        "module_name": "approve_appointment",
        "version": "1.0",
        "category": "Hospital",
        "description": "Requests manager approval",
        "inputs": [],
        "outputs": {"approval.status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["APPROVAL_REQUESTED"],
        "events_consumed": []
    },
    "send_reminder": {
        "module_name": "send_reminder",
        "version": "1.0",
        "category": "Hospital",
        "description": "Schedules appointment reminders",
        "inputs": [],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "complete_consultation": {
        "module_name": "complete_consultation",
        "version": "1.0",
        "category": "Hospital",
        "description": "Completes clinic consultation",
        "inputs": [],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "select_service": {
        "module_name": "select_service",
        "version": "1.0",
        "category": "Salon",
        "description": "Selects salon service",
        "inputs": ["str"],
        "outputs": {"salon.service_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "confirm_booking": {
        "module_name": "confirm_booking",
        "version": "1.0",
        "category": "Salon",
        "description": "Confirms scheduled booking",
        "inputs": [],
        "outputs": {"booking.status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["BOOKING_CREATED"],
        "events_consumed": []
    },
    "complete_service": {
        "module_name": "complete_service",
        "version": "1.0",
        "category": "Salon",
        "description": "Completes salon service",
        "inputs": [],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "browse_catalog": {
        "module_name": "browse_catalog",
        "version": "1.0",
        "category": "Supermarket",
        "description": "Browse catalog items",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "add_to_cart": {
        "module_name": "add_to_cart",
        "version": "1.0",
        "category": "Supermarket",
        "description": "Adds items to supermarket cart",
        "inputs": ["str"],
        "outputs": {"order.items": "list"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "payment": {
        "module_name": "payment",
        "version": "1.0",
        "category": "Supermarket",
        "description": "Process payment checkout",
        "inputs": [],
        "outputs": {"payment.status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["PAYMENT_REQUIRED"],
        "events_consumed": []
    },
    "delivery": {
        "module_name": "delivery",
        "version": "1.0",
        "category": "Supermarket",
        "description": "Create supermarket delivery",
        "inputs": [],
        "outputs": {"logistics.status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["DELIVERY_CREATED"],
        "events_consumed": []
    },
    "feedback": {
        "module_name": "feedback",
        "version": "1.0",
        "category": "Supermarket",
        "description": "Collects supermarket feedback",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "course_selection": {
        "module_name": "course_selection",
        "version": "1.0",
        "category": "Education",
        "description": "Selects course from catalog",
        "inputs": ["str"],
        "outputs": {"education.course_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "registration": {
        "module_name": "registration",
        "version": "1.0",
        "category": "Education",
        "description": "Processes registration request",
        "inputs": ["str"],
        "outputs": {"education.registration_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "enrollment_confirmation": {
        "module_name": "enrollment_confirmation",
        "version": "1.0",
        "category": "Education",
        "description": "Confirms student enrollment",
        "inputs": [],
        "outputs": {"education.enrollment_status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "support": {
        "module_name": "support",
        "version": "1.0",
        "category": "Education",
        "description": "Student academic support support",
        "inputs": ["str"],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["SUPPORT_REQUESTED"],
        "events_consumed": []
    },
    "capture_lead": {
        "module_name": "capture_lead",
        "version": "1.0",
        "category": "RealEstate",
        "description": "Captures lead details",
        "inputs": ["str"],
        "outputs": {"realestate.lead_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "assign_agent": {
        "module_name": "assign_agent",
        "version": "1.0",
        "category": "RealEstate",
        "description": "Assigns lead agent",
        "inputs": [],
        "outputs": {"realestate.agent_id": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "schedule_visit": {
        "module_name": "schedule_visit",
        "version": "1.0",
        "category": "RealEstate",
        "description": "Schedules viewing visit",
        "inputs": ["str"],
        "outputs": {"realestate.visit_time": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    },
    "confirm_visit": {
        "module_name": "confirm_visit",
        "version": "1.0",
        "category": "RealEstate",
        "description": "Confirms property visit",
        "inputs": [],
        "outputs": {"realestate.visit_status": "str"},
        "required_config": [],
        "optional_config": [],
        "events_emitted": ["BOOKING_CREATED"],
        "events_consumed": []
    },
    "follow_up": {
        "module_name": "follow_up",
        "version": "1.0",
        "category": "RealEstate",
        "description": "Follows up with lead",
        "inputs": [],
        "outputs": {},
        "required_config": [],
        "optional_config": [],
        "events_emitted": [],
        "events_consumed": []
    }
}

VALID_CATEGORIES = {
    "Core", "Restaurant", "Salon", "Clinic", "Hospital", "Gym", "Ecommerce",
    "RealEstate", "Education", "ServiceBusiness", "Pharmacy", "Hotel", "Travel"
}

class CapabilityRegistry:
    @classmethod
    def get(cls, module_name: str, version: str = "1.0") -> Optional[Dict[str, Any]]:
        spec = CAPABILITIES_DATA.get(module_name)
        if spec and spec["version"] == version:
            return spec
        return None

    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        return list(CAPABILITIES_DATA.values())

    @classmethod
    def list_by_category(cls, category: str) -> List[Dict[str, Any]]:
        return [spec for spec in CAPABILITIES_DATA.values() if spec["category"].lower() == category.lower()]

    @classmethod
    def initialize_capabilities_directory(cls, root_dir: str = ".") -> None:
        """
        Dynamically initializes the capabilities/ directory structure
        by writing capability specifications to their category folders.
        """
        capabilities_dir = os.path.join(root_dir, "capabilities")
        os.makedirs(capabilities_dir, exist_ok=True)
        
        # Create category folders
        for cat in VALID_CATEGORIES:
            cat_folder = cat.lower().replace(" ", "_")
            cat_path = os.path.join(capabilities_dir, cat_folder)
            os.makedirs(cat_path, exist_ok=True)
            
        # Write specs to JSON files
        for name, spec in CAPABILITIES_DATA.items():
            cat_folder = spec["category"].lower().replace(" ", "_")
            file_path = os.path.join(capabilities_dir, cat_folder, f"{name}.json")
            try:
                with open(file_path, "w") as f:
                    json.dump(spec, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to write capability spec for {name}: {str(e)}")
                
        logger.info("Capability Library folder structure initialized successfully.")
