"""
CSA Step 3 — Assurance Activity: Authentication Compliance

Tests that 21 CFR Part 11 session timeouts and password complexity rules
are strictly enforced by the system.
"""
import pytest
from datetime import timedelta
from jose import jwt

from demo_app.app.routes.auth import (
    validate_password_complexity,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

class TestPasswordComplexity:
    """Verify 21 CFR Part 11 §11.300 Password Complexity Enforcement."""
    
    def test_password_length_enforcement(self):
        with pytest.raises(ValueError, match="Password must be at least 8 characters long"):
            validate_password_complexity("Abc!12")
            
    def test_password_uppercase_enforcement(self):
        with pytest.raises(ValueError, match="Password must contain at least one uppercase letter"):
            validate_password_complexity("lowercase!123")
            
    def test_password_lowercase_enforcement(self):
        with pytest.raises(ValueError, match="Password must contain at least one lowercase letter"):
            validate_password_complexity("UPPERCASE!123")
            
    def test_password_number_enforcement(self):
        with pytest.raises(ValueError, match="Password must contain at least one number"):
            validate_password_complexity("NoNumbersHere!")
            
    def test_password_special_char_enforcement(self):
        with pytest.raises(ValueError, match="Password must contain at least one special character"):
            validate_password_complexity("NoSpecialChars123")
            
    def test_compliant_password_accepted(self):
        # Should not raise an exception
        validate_password_complexity("ValidP@ssw0rd")
        
class TestSessionTimeout:
    """Verify 21 CFR Part 11 session timeouts."""
    
    def test_access_token_uses_strict_timeout(self):
        assert ACCESS_TOKEN_EXPIRE_MINUTES == 15
        
        token = create_access_token({"sub": "test_user"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        import time
        # token `exp` should be roughly 15 minutes from now
        expires_in_seconds = payload["exp"] - time.time()
        
        # 15 mins = 900 seconds. Allow slight execution time diff.
        assert 890 <= expires_in_seconds <= 905
