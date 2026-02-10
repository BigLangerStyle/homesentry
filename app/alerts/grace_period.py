"""
Grace period tracking for sustained state changes.

Prevents alerting on transient flaps by requiring N consecutive
bad checks before logging events and sending alerts.

This module implements "sustained state checking" - a common pattern in
monitoring systems to reduce alert noise from brief network hiccups,
service restarts, or temporary resource spikes.

How it works:
1. When a bad state is first detected, it's marked as "pending"
2. Each subsequent check increments the consecutive check counter
3. Only after N consecutive bad checks does the alert proceed
4. If status recovers before threshold, pending state is discarded
5. Recovery to OK always proceeds immediately (no grace period)

Example:
    Service flaps (brief):
        Check 1: OK → FAIL (pending, count=1)
        Check 2: FAIL (pending, count=2)
        Check 3: FAIL → OK (recovered, pending cleared, no alert sent)
    
    Service sustained failure:
        Check 1: OK → FAIL (pending, count=1)
        Check 2: FAIL (pending, count=2)
        Check 3: FAIL (count=3, threshold met, alert proceeds)
        Check 4: FAIL (already alerted, normal rules apply)
"""
import logging
import os
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# In-memory tracker for pending state changes
# Key: event_key (e.g., "service_plex")
# Value: PendingState object
_pending_states: Dict[str, "PendingState"] = {}

# Configuration
GRACE_CHECKS = int(os.getenv("STATE_CHANGE_GRACE_CHECKS", "3"))


@dataclass
class PendingState:
    """Track a pending state change during grace period."""
    event_key: str
    bad_status: str  # WARN or FAIL
    prev_status: Optional[str]  # Status before the bad state
    first_seen_ts: datetime  # When first detected
    consecutive_checks: int  # How many consecutive bad checks


async def check_grace_period(
    event_key: str,
    current_status: str,
    prev_status: Optional[str]
) -> tuple[bool, str]:
    """
    Check if alert should proceed based on grace period.
    
    This is the main entry point for grace period logic. Call this BEFORE
    the existing should_alert() logic in rules.py.
    
    Args:
        event_key: Unique event identifier (e.g., "service_plex")
        current_status: Current status (OK/WARN/FAIL)
        prev_status: Previous status from database (OK/WARN/FAIL or None)
    
    Returns:
        tuple[bool, str]: (should_proceed, reason)
            - (True, "reason") if alert should proceed to normal processing
            - (False, "reason") if alert should be suppressed (grace period)
    
    Logic:
        - Recovery to OK: Always proceed immediately
        - First bad state or worsening: Check grace period
        - Status change within bad states (WARN↔FAIL): Continue tracking
        - Grace period met: Proceed with normal alert logic
    
    Examples:
        >>> # First detection of failure
        >>> await check_grace_period("service_plex", "FAIL", "OK")
        (False, "Started grace period (1/3)")
        
        >>> # Second consecutive failure
        >>> await check_grace_period("service_plex", "FAIL", "OK")
        (False, "In grace period (2/3)")
        
        >>> # Third consecutive failure - threshold met
        >>> await check_grace_period("service_plex", "FAIL", "OK")
        (True, "Grace period passed (3 checks)")
        
        >>> # Recovery before threshold
        >>> await check_grace_period("service_plex", "OK", "OK")
        (True, "Recovery to OK - immediate alert")
    """
    # Recovery to OK always proceeds immediately (no grace period for good news)
    if current_status == "OK":
        # Clean up any pending state
        if event_key in _pending_states:
            pending = _pending_states[event_key]
            logger.info(
                f"Recovery detected for {event_key} during grace period "
                f"({pending.consecutive_checks}/{GRACE_CHECKS} checks) - "
                f"discarding pending state"
            )
            del _pending_states[event_key]
        
        return True, "Recovery to OK - immediate alert"
    
    # If no previous status (first time seeing this event), start grace period
    if prev_status is None:
        _pending_states[event_key] = PendingState(
            event_key=event_key,
            bad_status=current_status,
            prev_status=prev_status,
            first_seen_ts=datetime.now(),
            consecutive_checks=1
        )
        logger.info(
            f"First detection of {event_key} in {current_status} state - "
            f"started grace period (1/{GRACE_CHECKS})"
        )
        return False, f"Started grace period (1/{GRACE_CHECKS})"
    
    # If transitioning from OK to bad (WARN or FAIL)
    if prev_status == "OK" and current_status in ("WARN", "FAIL"):
        # Check if already tracking this
        if event_key in _pending_states:
            pending = _pending_states[event_key]
            pending.consecutive_checks += 1
            
            if pending.consecutive_checks >= GRACE_CHECKS:
                # Grace period passed - allow alert to proceed
                logger.info(
                    f"Grace period passed for {event_key} "
                    f"({pending.consecutive_checks} consecutive {current_status} checks)"
                )
                del _pending_states[event_key]
                return True, f"Grace period passed ({pending.consecutive_checks} checks)"
            else:
                # Still in grace period
                logger.info(
                    f"In grace period for {event_key} "
                    f"({pending.consecutive_checks}/{GRACE_CHECKS} checks)"
                )
                return False, f"In grace period ({pending.consecutive_checks}/{GRACE_CHECKS})"
        else:
            # Start tracking
            _pending_states[event_key] = PendingState(
                event_key=event_key,
                bad_status=current_status,
                prev_status=prev_status,
                first_seen_ts=datetime.now(),
                consecutive_checks=1
            )
            logger.info(
                f"Started grace period for {event_key} "
                f"(OK → {current_status}, 1/{GRACE_CHECKS})"
            )
            return False, f"Started grace period (1/{GRACE_CHECKS})"
    
    # Status change within bad states (WARN→FAIL or FAIL→WARN)
    # This is still a problem, so continue tracking
    if prev_status in ("WARN", "FAIL") and current_status in ("WARN", "FAIL"):
        if event_key in _pending_states:
            pending = _pending_states[event_key]
            pending.consecutive_checks += 1
            pending.bad_status = current_status  # Update to new status
            
            if pending.consecutive_checks >= GRACE_CHECKS:
                # Grace period passed with status change
                logger.info(
                    f"Grace period passed for {event_key} with status change "
                    f"({pending.consecutive_checks} checks, now {current_status})"
                )
                del _pending_states[event_key]
                return True, f"Grace period passed with status change ({pending.consecutive_checks} checks)"
            else:
                # Still in grace period
                logger.info(
                    f"In grace period for {event_key} with status change "
                    f"({pending.consecutive_checks}/{GRACE_CHECKS} checks, now {current_status})"
                )
                return False, f"In grace period with status change ({pending.consecutive_checks}/{GRACE_CHECKS})"
        else:
            # Not tracking yet - this shouldn't happen in normal flow, but handle it
            logger.warning(
                f"Status change {prev_status}→{current_status} for {event_key} "
                f"without pending state - proceeding with alert"
            )
            return True, "Status change detected (not in grace period)"
    
    # Default: proceed with alert (covers edge cases)
    # This includes cases where status improved (FAIL→WARN) after grace period
    return True, "Default proceed"


def clear_pending_state(event_key: str) -> None:
    """
    Clear pending state for an event (used on recovery).
    
    This is called when a service recovers before the grace period
    threshold is met. It prevents the pending state from affecting
    future checks.
    
    Args:
        event_key: Unique event identifier
    
    Example:
        >>> clear_pending_state("service_plex")
    """
    if event_key in _pending_states:
        logger.debug(f"Cleared pending state for {event_key}")
        del _pending_states[event_key]


def get_pending_states() -> Dict[str, PendingState]:
    """
    Get all pending states (for debugging/monitoring).
    
    Returns:
        Dict mapping event_key to PendingState
    
    Example:
        >>> states = get_pending_states()
        >>> for key, state in states.items():
        ...     print(f"{key}: {state.consecutive_checks}/{GRACE_CHECKS} checks")
    """
    return _pending_states.copy()


def reset_grace_period() -> None:
    """
    Reset all grace period state (for testing).
    
    This clears all pending states. Useful for unit tests or
    manual intervention.
    
    Example:
        >>> reset_grace_period()
        >>> assert len(get_pending_states()) == 0
    """
    global _pending_states
    _pending_states = {}
    logger.info("Grace period state reset")
