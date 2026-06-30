import streamlit as st
import streamlit.components.v1 as components


def render_caps_lock_detector():
    """페이지 내 password 입력에 Caps Lock 경고를 표시."""
    components.html(
        """
        <div id="caps-lock-banner"
             style="display:none; color:#d9534f; font-size:13px; font-weight:600;
                    margin-bottom:8px; font-family:sans-serif;">
            ⚠ Caps Lock이 켜져 있습니다
        </div>
        <script>
        (function () {
            const banner = document.getElementById("caps-lock-banner");
            const parentDoc = window.parent.document;

            function updateBanner(e) {
                const active = parentDoc.activeElement;
                const isPassword =
                    active &&
                    (active.type === "password" ||
                     active.getAttribute("type") === "password" ||
                     active.getAttribute("autocomplete") === "current-password" ||
                     active.getAttribute("autocomplete") === "new-password");
                if (isPassword && e.getModifierState && e.getModifierState("CapsLock")) {
                    banner.style.display = "block";
                } else if (!e.getModifierState || !e.getModifierState("CapsLock")) {
                    banner.style.display = "none";
                }
            }

            parentDoc.addEventListener("keydown", updateBanner, true);
            parentDoc.addEventListener("keyup", updateBanner, true);
        })();
        </script>
        """,
        height=36,
    )


def password_field(label: str, key: str, placeholder: str = "") -> str:
    return st.text_input(label, type="password", key=key, placeholder=placeholder)
