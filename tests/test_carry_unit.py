import pytest
from src.schemas.carry_unit import CarryUnit

def test_carry_unit_initialization():
    cu = CarryUnit(
        session={
            "session_id": "sess_123",
            "customer_phone": "+19998887777",
            "business_id": "biz_456",
            "workflow_version_id": "wf_789",
            "session_started_at": "2026-05-24T18:00:00Z"
        }
    )
    assert cu.version == 1
    assert cu.session.session_id == "sess_123"
    assert cu.order.total == 0.0

def test_carry_unit_session_immutability():
    cu = CarryUnit(
        session={
            "session_id": "sess_123",
            "customer_phone": "+19998887777",
            "business_id": "biz_456",
            "workflow_version_id": "wf_789",
            "session_started_at": "2026-05-24T18:00:00Z"
        }
    )

    # Merging identical session details should pass and increment version
    cu2 = cu.merge_patch({"session": {"session_id": "sess_123"}})
    assert cu2.version == 2

    # Modifying session ID should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        cu.merge_patch({"session": {"session_id": "sess_changed"}})
    assert "session namespace is immutable" in str(exc_info.value)

def test_carry_unit_order_items_append_only():
    cu = CarryUnit(
        session={
            "session_id": "sess_123",
            "customer_phone": "+19998887777",
            "business_id": "biz_456",
            "workflow_version_id": "wf_789",
            "session_started_at": "2026-05-24T18:00:00Z"
        }
    )
    
    # Add initial item
    cu = cu.merge_patch({
        "order": {
            "items": [{"item_id": "pizza", "quantity": 1, "price": 12.00}],
            "total": 12.00
        }
    })
    assert len(cu.order.items) == 1
    assert cu.order.total == 12.00

    # Add second item - check it appends, not overwrites
    cu = cu.merge_patch({
        "order": {
            "items": [{"item_id": "fries", "quantity": 2, "price": 4.00}],
            "total": 20.00
        }
    })
    assert len(cu.order.items) == 2
    assert cu.order.items[0].item_id == "pizza"
    assert cu.order.items[1].item_id == "fries"
    assert cu.order.total == 20.00

def test_carry_unit_payment_status_lock():
    cu = CarryUnit(
        session={
            "session_id": "sess_123",
            "customer_phone": "+19998887777",
            "business_id": "biz_456",
            "workflow_version_id": "wf_789",
            "session_started_at": "2026-05-24T18:00:00Z"
        }
    )
    
    # Transition to SUCCESS
    cu = cu.merge_patch({"payment": {"status": "SUCCESS"}})
    assert cu.payment.status == "SUCCESS"

    # Attempt to change away from SUCCESS should fail
    with pytest.raises(ValueError) as exc_info:
        cu.merge_patch({"payment": {"status": "FAILED"}})
    assert "payment status is locked" in str(exc_info.value)
