"""
User authentication system for Streamlit
Uses streamlit-authenticator with database backend
"""

import streamlit as st
import bcrypt
from typing import Optional, Dict
from datetime import datetime, timedelta
import secrets
from dashboard.multiuser.database import MultiUserDatabase


class AuthManager:
    """Manages user authentication and sessions"""

    def __init__(self, db: MultiUserDatabase):
        self.db = db

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

    def register_user(self, email: str, password: str, full_name: str = None) -> tuple[bool, str]:
        """
        Register a new user
        Returns: (success: bool, message: str)
        """
        # Validate email
        if not email or '@' not in email:
            return False, "Invalid email address"

        # Validate password
        if len(password) < 8:
            return False, "Password must be at least 8 characters"

        # Check if user exists
        existing_user = self.db.get_user_by_email(email)
        if existing_user:
            return False, "User with this email already exists"

        try:
            # Hash password and create user
            password_hash = self.hash_password(password)
            user_id = self.db.create_user(email, password_hash, full_name)

            return True, f"User created successfully! User ID: {user_id}"

        except Exception as e:
            return False, f"Error creating user: {str(e)}"

    def login_user(self, email: str, password: str) -> tuple[bool, Optional[Dict], str]:
        """
        Login user
        Returns: (success: bool, user: Optional[Dict], message: str)
        """
        # Get user from database
        user = self.db.get_user_by_email(email)

        if not user:
            return False, None, "Invalid email or password"

        # Check if user is active
        if not user.get('is_active'):
            return False, None, "Account is deactivated. Please contact support."

        # Verify password
        if not self.verify_password(password, user['password_hash']):
            return False, None, "Invalid email or password"

        # Update last login
        self.db.update_last_login(user['id'])

        # Remove password hash from returned user object
        user_safe = {k: v for k, v in user.items() if k != 'password_hash'}

        return True, user_safe, "Login successful!"

    def logout_user(self):
        """Logout current user"""
        for key in list(st.session_state.keys()):
            del st.session_state[key]

    def get_current_user(self) -> Optional[Dict]:
        """Get currently logged in user from session"""
        return st.session_state.get('user')

    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return 'user' in st.session_state and st.session_state.user is not None

    def require_auth(self):
        """Decorator/check to require authentication"""
        if not self.is_authenticated():
            st.warning("Please login to access this page")
            st.stop()

    def set_session(self, user: Dict):
        """Set user session"""
        st.session_state.user = user
        st.session_state.user_id = user['id']
        st.session_state.user_email = user['email']
        st.session_state.authenticated = True


def show_login_page(auth_manager: AuthManager):
    """Display login page"""
    st.markdown("<h1 style='text-align: center;'>🔐 Login to TradingAgents</h1>", unsafe_allow_html=True)

    # Create tabs for Login and Signup
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        st.markdown("### Login to Your Account")

        with st.form("login_form"):
            email = st.text_input("Email", placeholder="your@email.com")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)

            if submit:
                if not email or not password:
                    st.error("Please enter both email and password")
                else:
                    success, user, message = auth_manager.login_user(email, password)

                    if success:
                        auth_manager.set_session(user)
                        st.success(message)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(message)

    with tab2:
        st.markdown("### Create New Account")

        with st.form("signup_form"):
            new_email = st.text_input("Email", key="signup_email", placeholder="your@email.com")
            new_name = st.text_input("Full Name", placeholder="John Doe")
            new_password = st.text_input("Password", type="password", key="signup_password", help="Minimum 8 characters")
            confirm_password = st.text_input("Confirm Password", type="password")
            agree_terms = st.checkbox("I agree to the Terms of Service and Privacy Policy")
            submit_signup = st.form_submit_button("Create Account", use_container_width=True)

            if submit_signup:
                if not new_email or not new_password:
                    st.error("Please fill in all required fields")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                elif not agree_terms:
                    st.error("Please agree to the Terms of Service")
                else:
                    success, message = auth_manager.register_user(new_email, new_password, new_name)

                    if success:
                        st.success(message)
                        st.info("Please login with your credentials")
                    else:
                        st.error(message)

    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #666;'>
        <p>By using TradingAgents, you agree to our Terms of Service and Privacy Policy.</p>
        <p>This platform is for educational purposes only and does not constitute financial advice.</p>
        </div>
    """, unsafe_allow_html=True)


def show_user_menu(auth_manager: AuthManager):
    """Display user menu in sidebar"""
    user = auth_manager.get_current_user()

    if user:
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"### 👤 {user.get('full_name', user['email'])}")
        st.sidebar.caption(f"📧 {user['email']}")

        # Subscription info
        tier = user.get('subscription_tier', 'free')
        tier_emoji = {"free": "🆓", "basic": "⭐", "pro": "💎", "enterprise": "👑"}
        st.sidebar.markdown(f"**Plan:** {tier_emoji.get(tier, '🆓')} {tier.title()}")

        # Usage stats
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.metric("Analyses", user.get('total_analyses', 0))
        with col2:
            st.metric("Trades", user.get('total_trades', 0))

        # Logout button
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            auth_manager.logout_user()
            st.rerun()
