from typing import Type
import time

class RetryAction:
    def __init__(self, should_retry: bool, backoff_seconds: float = 0.0, is_fatal: bool = False, mark_unavailable: bool = False):
        self.should_retry = should_retry
        self.backoff_seconds = backoff_seconds
        self.is_fatal = is_fatal
        self.mark_unavailable = mark_unavailable

class RetryPolicy:
    """
    Centralized retry classification engine.
    Maps execution exceptions to operational policies.
    """
    @staticmethod
    def classify(exception: Exception) -> RetryAction:
        err_msg = str(exception).lower()
        
        # 1. Quota / Rate Limits (429)
        if "429" in err_msg or "rate limit" in err_msg or "too many requests" in err_msg:
            return RetryAction(should_retry=True, backoff_seconds=5.0, mark_unavailable=True)
            
        # 2. Malformed JSON / Schema mismatch
        if "malformed json" in err_msg or "jsondecodeerror" in err_msg or "validationerror" in err_msg:
            # Retry immediately on another provider
            return RetryAction(should_retry=True, backoff_seconds=0.0)
            
        # 3. Content Blocked / Safety
        if "safety" in err_msg or "blocked" in err_msg:
            return RetryAction(should_retry=False, is_fatal=True)
            
        # 4. Authentication issues
        if "auth" in err_msg or "api key" in err_msg or "unauthorized" in err_msg:
            return RetryAction(should_retry=False, is_fatal=True, mark_unavailable=True)
            
        # 5. Network Timeout / Server 500s
        return RetryAction(should_retry=True, backoff_seconds=2.0)
