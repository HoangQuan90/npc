DOMAIN = "npc"

# Config keys
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_CUSTOMER_ID = "customer_id"
CONF_REGION = "region"
CONF_NGAYDAUKY = "ngaydauky"

# Regions
REGION_HN = "HN"
REGION_NPC = "NPC"
REGION_CPC = "CPC"
REGION_SPC = "SPC"
REGION_HCMC = "HCMC"

# Tiền tố mã khách hàng của từng tổng công ty điện lực.
# Chọn sai khu vực thì đăng nhập và API tra cứu đều hỏng, nên dùng bảng này
# để cảnh báo ngay lúc cấu hình. Tiền tố lạ (không có trong bảng) thì bỏ qua.
CUSTOMER_ID_PREFIX_REGION = {
    "PD": REGION_HN,
    "PE": REGION_HCMC,
    "PA": REGION_NPC,
    "PH": REGION_NPC,
    "PM": REGION_NPC,
    "PN": REGION_NPC,
    "PC": REGION_CPC,
    "PP": REGION_CPC,
    "PQ": REGION_CPC,
    "PB": REGION_SPC,
    "PK": REGION_SPC,
}

# Database path
DB_PATH = "/config/evnvn/evndata.db"

# Scan interval
# EVN chỉ chốt chỉ số mỗi ngày một lần (số của hôm nay lên vào hôm sau), nên
# hỏi dày hơn 1 giờ chỉ tốn request mà không có dữ liệu mới.
SCAN_INTERVAL = 3600  # 1 hour

# Mỗi lần cập nhật chỉ tải lại ngần này ngày gần nhất. Dữ liệu cũ hơn không
# đổi nữa; toàn bộ lịch sử chỉ tải một lần khi database còn rỗng. Giữ vài ngày
# để đón các bản ghi EVN chốt muộn hoặc chốt gộp nhiều ngày.
REFRESH_WINDOW_DAYS = 7