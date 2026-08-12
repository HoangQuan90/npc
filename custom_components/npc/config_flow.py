"""Config flow for EVN VN integration"""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from typing import Any
import logging

from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_CUSTOMER_ID,
    CONF_REGION,
    CONF_NGAYDAUKY,
    REGION_HN,
    REGION_NPC,
    REGION_CPC,
    REGION_SPC,
    REGION_HCMC,
    CUSTOMER_ID_PREFIX_REGION,
)
from .npc_api import EVNAPI

_LOGGER = logging.getLogger(__name__)

REGION_OPTIONS = [
    {"value": REGION_HN, "label": "Hà Nội (HN)"},
    {"value": REGION_NPC, "label": "Miền Bắc (NPC)"},
    {"value": REGION_CPC, "label": "Miền Trung (CPC)"},
    {"value": REGION_SPC, "label": "Miền Nam (SPC)"},
    {"value": REGION_HCMC, "label": "Hồ Chí Minh (HCMC)"},
]


class EVNConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for EVN VN."""

    VERSION = 2

    def __init__(self):
        """Initialize config flow."""
        self._user_input = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle initial step - select region."""
        errors = {}

        if user_input is not None:
            self._user_input[CONF_REGION] = user_input[CONF_REGION]
            return await self.async_step_credentials()

        schema = vol.Schema({
            vol.Required(CONF_REGION): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=REGION_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN
                )
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "info": """
### 🔌 Cấu hình EVN VN

Chọn khu vực điện lực của bạn:
- **HN**: Hà Nội
- **NPC**: Miền Bắc
- **CPC**: Miền Trung  
- **SPC**: Miền Nam
- **HCMC**: Hồ Chí Minh
                """
            }
        )

    async def async_step_credentials(self, user_input: dict[str, Any] | None = None):
        """Handle credentials step."""
        errors = {}

        if user_input is not None:
            self._user_input.update({
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            })
            return await self.async_step_customer_id()

        schema = vol.Schema({
            vol.Required(CONF_USERNAME): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT,
                    autocomplete="username"
                )
            ),
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD
                )
            ),
        })

        return self.async_show_form(
            step_id="credentials",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "info": f"""
### 🔐 Thông tin đăng nhập

Nhập username và password để đăng nhập vào hệ thống EVN.

**Khu vực đã chọn**: {self._user_input.get(CONF_REGION, 'N/A')}
                """
            }
        )

    def _account_schema(self, prefill: dict) -> vol.Schema:
        """Form đầy đủ: khu vực + tài khoản + mật khẩu + mã + ngày đầu kỳ.

        Dùng chung cho bước thêm mới và bước reconfigure, điền sẵn từ prefill.
        """
        return vol.Schema({
            vol.Required(
                CONF_REGION,
                default=prefill.get(CONF_REGION, REGION_NPC)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=REGION_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN
                )
            ),
            vol.Required(
                CONF_USERNAME,
                default=prefill.get(CONF_USERNAME, "")
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT,
                    autocomplete="username"
                )
            ),
            vol.Required(
                CONF_PASSWORD,
                default=prefill.get(CONF_PASSWORD, "")
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD
                )
            ),
            vol.Required(
                CONF_CUSTOMER_ID,
                default=prefill.get(CONF_CUSTOMER_ID, "")
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT,
                    autocomplete="customer_id"
                )
            ),
            vol.Required(
                CONF_NGAYDAUKY,
                default=int(prefill.get(CONF_NGAYDAUKY, 1))
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=31,
                    mode=selector.NumberSelectorMode.SLIDER,
                    step=1
                )
            ),
        })

    async def _validate_account(self, region, username, password, customer_id):
        """Đăng nhập và thử lấy dữ liệu. Trả None nếu OK, ngược lại mã lỗi.

        Đây là chỗ tài khoản/mật khẩu vừa nhập được kiểm chứng thật: đăng nhập
        rồi gọi get_chisongay. "no_data" nghĩa là đăng nhập được nhưng tài khoản
        này không có quyền đọc mã đó — người dùng nhập mật khẩu đúng rồi thử lại.
        """
        expected_region = CUSTOMER_ID_PREFIX_REGION.get(customer_id[:2])
        if not (customer_id.startswith('P') or customer_id.startswith('S')) or len(customer_id) < 11:
            return "invalid_format"
        if expected_region and expected_region != region:
            _LOGGER.error(
                f"Mã khách hàng {customer_id} thuộc khu vực {expected_region}, "
                f"nhưng đang chọn {region}"
            )
            return "wrong_region"

        api = EVNAPI(self.hass, region, username, password, customer_id)
        try:
            if not await api.login():
                return "invalid_auth"
            from datetime import datetime, timedelta
            today = datetime.now()
            from_date = (today - timedelta(days=7)).strftime("%d/%m/%Y")
            to_date = today.strftime("%d/%m/%Y")
            test_data = await api.get_chisongay(from_date, to_date)
            if test_data and test_data.get("data"):
                return None
            return "no_data"
        except Exception as e:
            _LOGGER.error(f"Error during verification: {e}", exc_info=True)
            return "unknown"
        finally:
            try:
                await api.close()
            except Exception:
                pass

    async def async_step_customer_id(self, user_input: dict[str, Any] | None = None):
        """Handle customer ID and billing cycle step.

        Bước cuối gồm đủ khu vực + tài khoản + mật khẩu + mã + ngày đầu kỳ,
        điền sẵn từ các bước trước. Khi một mã lỗi vì cần tài khoản/khu vực
        khác (ví dụ mã miền Nam phải dùng tài khoản app SPC riêng), người dùng
        sửa ngay tại đây rồi thử lại, không phải làm lại từ đầu.
        """
        errors = {}

        # Giá trị điền sẵn: ưu tiên lần nhập gần nhất, rồi tới các bước trước.
        prefill = dict(self._user_input)
        if user_input:
            prefill.update(user_input)

        if user_input is not None:
            region = user_input[CONF_REGION]
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD]
            customer_id = user_input[CONF_CUSTOMER_ID].strip().upper()
            ngaydauky = int(user_input[CONF_NGAYDAUKY])

            # Nhớ lại để lần thử tiếp theo điền sẵn
            self._user_input.update({
                CONF_REGION: region,
                CONF_USERNAME: username,
                CONF_PASSWORD: password,
            })

            err = await self._validate_account(region, username, password, customer_id)
            if err == "invalid_format":
                errors[CONF_CUSTOMER_ID] = err
            elif err:
                errors["base"] = err
            else:
                await self.async_set_unique_id(customer_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=customer_id,
                    data={
                        CONF_REGION: region,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_CUSTOMER_ID: customer_id,
                        CONF_NGAYDAUKY: ngaydauky,
                    }
                )

        return self.async_show_form(
            step_id="customer_id",
            data_schema=self._account_schema(prefill),
            errors=errors,
            description_placeholders={
                "info": """
### 📋 Thông tin tài khoản

Mỗi mã khách hàng là một lần thêm riêng và có thể dùng **tài khoản riêng**.
Nếu một mã báo lỗi vì cần tài khoản hoặc khu vực khác, sửa ngay các ô bên
dưới rồi bấm gửi lại — không cần làm lại từ đầu.

**Ngày đầu kỳ**: Ngày bắt đầu chu kỳ thanh toán hàng tháng (1-31)
                """
            }
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Cấu hình lại một entry đã có mà không cần xóa.

        Đúng nhu cầu: một mã đã thêm nhưng không ra dữ liệu, mở reconfigure để
        nhập lại mật khẩu (hoặc đổi khu vực/tài khoản) đúng, thử lại, cập nhật
        tại chỗ. Mở từ menu ⋮ của entry → Cấu hình lại.
        """
        errors = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        prefill = {**entry.data, **entry.options}
        if user_input:
            prefill.update(user_input)

        if user_input is not None:
            region = user_input[CONF_REGION]
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD]
            customer_id = user_input[CONF_CUSTOMER_ID].strip().upper()
            ngaydauky = int(user_input[CONF_NGAYDAUKY])

            err = await self._validate_account(region, username, password, customer_id)
            if err == "invalid_format":
                errors[CONF_CUSTOMER_ID] = err
            elif err:
                errors["base"] = err
            else:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        CONF_REGION: region,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_CUSTOMER_ID: customer_id,
                        CONF_NGAYDAUKY: ngaydauky,
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self._account_schema(prefill),
            errors=errors,
            description_placeholders={
                "info": """
### 🔧 Nhập lại tài khoản cho mã này

Mã này chưa lấy được dữ liệu với tài khoản hiện tại. Nhập **mật khẩu đúng**
(hoặc đổi khu vực/tên đăng nhập) rồi bấm gửi để thử lại và cập nhật.
                """
            }
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get options flow handler."""
        return EVNOptionsFlowHandler(config_entry)


class EVNOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Initialize options step."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_ngaydauky = self.config_entry.options.get(
            CONF_NGAYDAUKY,
            self.config_entry.data.get(CONF_NGAYDAUKY, 1)
        )

        schema = vol.Schema({
            vol.Required(
                CONF_NGAYDAUKY,
                default=current_ngaydauky
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=31,
                    mode=selector.NumberSelectorMode.BOX
                )
            ),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema
        )
