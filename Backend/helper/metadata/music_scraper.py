import asyncio
import re
import urllib.parse
import httpx
from typing import Dict, Optional, Tuple, List
from Backend.logger import LOGGER

_METADATA_CACHE: Dict[str, dict] = {}

# ─────────────────────────────────────────────────────────────
# 1. BẢNG QUY CHUẨN THỂ LOẠI (GENRE TAXONOMY MAP)
# Chuẩn hóa hơn 100+ tag thô từ iTunes, Deezer, Shazam, ID3 về 16 nhóm chuẩn
# ─────────────────────────────────────────────────────────────
GENRE_TAXONOMY_MAP: Dict[str, str] = {
    # Pop / Ballad / Nhạc Trẻ
    "pop": "Pop / Ballad",
    "ballad": "Pop / Ballad",
    "v-pop": "V-Pop / Nhạc Trẻ",
    "vpop": "V-Pop / Nhạc Trẻ",
    "vietnamese pop": "V-Pop / Nhạc Trẻ",
    "vietnamese": "V-Pop / Nhạc Trẻ",
    "nhạc trẻ": "V-Pop / Nhạc Trẻ",
    "c-pop": "Pop / Ballad",
    "cpop": "Pop / Ballad",
    "mandopop": "Pop / Ballad",
    "cantopop": "Pop / Ballad",
    "k-pop": "Pop / Ballad",
    "kpop": "Pop / Ballad",
    "korean pop": "Pop / Ballad",
    "j-pop": "Pop / Ballad",
    "jpop": "Pop / Ballad",
    "japanese pop": "Pop / Ballad",
    "adult contemporary": "Pop / Ballad",
    "dance-pop": "Pop / Ballad",
    "synth-pop": "Pop / Ballad",
    "indie pop": "Pop / Ballad",
    "teen pop": "Pop / Ballad",
    "chanson": "Pop / Ballad",

    # Bolero / Trữ Tình / Dân Ca
    "bolero": "Bolero / Trữ Tình",
    "trữ tình": "Bolero / Trữ Tình",
    "nhạc vàng": "Bolero / Trữ Tình",
    "dân ca": "Bolero / Trữ Tình",
    "quê hương": "Bolero / Trữ Tình",
    "tân cổ": "Bolero / Trữ Tình",
    "cải lương": "Bolero / Trữ Tình",

    # EDM / Dance / Remix / Vinahouse
    "electronic": "EDM / Remix",
    "dance": "EDM / Remix",
    "edm": "EDM / Remix",
    "remix": "EDM / Remix",
    "house": "EDM / Remix",
    "vinahouse": "EDM / Remix",
    "techno": "EDM / Remix",
    "trance": "EDM / Remix",
    "dubstep": "EDM / Remix",
    "electro": "EDM / Remix",
    "club": "EDM / Remix",
    "hardstyle": "EDM / Remix",
    "trap edm": "EDM / Remix",
    "drum & bass": "EDM / Remix",
    "dnb": "EDM / Remix",
    "electronica": "EDM / Remix",
    "deep house": "EDM / Remix",
    "future bass": "EDM / Remix",

    # Rap / Hip-Hop
    "hip-hop/rap": "Rap / Hip-Hop",
    "hip-hop": "Rap / Hip-Hop",
    "hip hop": "Rap / Hip-Hop",
    "rap": "Rap / Hip-Hop",
    "rap việt": "Rap / Hip-Hop",
    "trap": "Rap / Hip-Hop",
    "drill": "Rap / Hip-Hop",
    "underground rap": "Rap / Hip-Hop",
    "boom bap": "Rap / Hip-Hop",
    "gangsta rap": "Rap / Hip-Hop",
    "hardcore rap": "Rap / Hip-Hop",

    # R&B / Soul / Funk
    "r&b/soul": "R&B / Soul",
    "r&b": "R&B / Soul",
    "contemporary r&b": "R&B / Soul",
    "soul": "R&B / Soul",
    "neo-soul": "R&B / Soul",
    "funk": "R&B / Soul",
    "disco": "R&B / Soul",
    "motown": "R&B / Soul",

    # Rock / Indie / Metal
    "rock": "Rock / Indie",
    "alternative": "Rock / Indie",
    "alternative rock": "Rock / Indie",
    "indie": "Rock / Indie",
    "indie rock": "Rock / Indie",
    "hard rock": "Rock / Indie",
    "metal": "Rock / Indie",
    "heavy metal": "Rock / Indie",
    "punk": "Rock / Indie",
    "punk rock": "Rock / Indie",
    "grunge": "Rock / Indie",
    "progressive rock": "Rock / Indie",
    "psychedelic rock": "Rock / Indie",

    # Acoustic / Chill / Lofi
    "acoustic": "Acoustic / Chill / Lofi",
    "lofi": "Acoustic / Chill / Lofi",
    "lo-fi": "Acoustic / Chill / Lofi",
    "chill": "Acoustic / Chill / Lofi",
    "chillout": "Acoustic / Chill / Lofi",
    "ambient": "Acoustic / Chill / Lofi",
    "downtempo": "Acoustic / Chill / Lofi",
    "coffee": "Acoustic / Chill / Lofi",
    "relax": "Acoustic / Chill / Lofi",
    "unplugged": "Acoustic / Chill / Lofi",
    "singer/songwriter": "Acoustic / Chill / Lofi",
    "folk-pop": "Acoustic / Chill / Lofi",

    # Nhạc Phim / Soundtrack / OST
    "soundtrack": "Nhạc Phim / OST",
    "ost": "Nhạc Phim / OST",
    "score": "Nhạc Phim / OST",
    "original score": "Nhạc Phim / OST",
    "original soundtrack": "Nhạc Phim / OST",
    "tv soundtrack": "Nhạc Phim / OST",
    "film score": "Nhạc Phim / OST",
    "anime": "Nhạc Phim / OST",
    "video game": "Nhạc Phim / OST",
    "musical": "Nhạc Phim / OST",

    # Cổ Điển / Classical / Instrumental
    "classical": "Cổ Điển / Classical",
    "cổ điển": "Cổ Điển / Classical",
    "orchestral": "Cổ Điển / Classical",
    "symphony": "Cổ Điển / Classical",
    "opera": "Cổ Điển / Classical",
    "chamber music": "Cổ Điển / Classical",
    "baroque": "Cổ Điển / Classical",
    "piano": "Cổ Điển / Classical",
    "instrumental": "Cổ Điển / Classical",
    "không lời": "Cổ Điển / Classical",
    "tân cổ điển": "Cổ Điển / Classical",
    "neoclassical": "Cổ Điển / Classical",

    # Jazz / Blues
    "jazz": "Jazz / Blues",
    "blues": "Jazz / Blues",
    "smooth jazz": "Jazz / Blues",
    "vocal jazz": "Jazz / Blues",
    "bossa nova": "Jazz / Blues",
    "bebop": "Jazz / Blues",
    "fusion": "Jazz / Blues",

    # Nhạc Đỏ / Cách Mạng
    "nhạc đỏ": "Nhạc Đỏ / Cách Mạng",
    "cách mạng": "Nhạc Đỏ / Cách Mạng",
    "tiền chiến": "Nhạc Đỏ / Cách Mạng",
    "hành khúc": "Nhạc Đỏ / Cách Mạng",

    # Country / Folk
    "country": "Country / Folk",
    "folk": "Country / Folk",
    "bluegrass": "Country / Folk",
    "americana": "Country / Folk",
    "contemporary country": "Country / Folk",

    # Latin / Reggae
    "latin": "Latin / Reggae",
    "latin urban": "Latin / Reggae",
    "reggae": "Latin / Reggae",
    "reggaeton": "Latin / Reggae",
    "salsa": "Latin / Reggae",
    "bachata": "Latin / Reggae",
    "flamenco": "Latin / Reggae",
    "afrobeat": "Latin / Reggae",

    # Thiếu Nhi / Kids
    "children's music": "Thiếu Nhi / Kids",
    "kids": "Thiếu Nhi / Kids",
    "thiếu nhi": "Thiếu Nhi / Kids",
    "nursery rhymes": "Thiếu Nhi / Kids",

    # Podcast / Sách Nói
    "podcast": "Podcast / Sách Nói",
    "audiobook": "Podcast / Sách Nói",
    "sách nói": "Podcast / Sách Nói",
    "spoken word": "Podcast / Sách Nói",
    "speech": "Podcast / Sách Nói"
}


def normalize_raw_genre(raw: str) -> str:
    """Chuẩn hóa một chuỗi genre thô về nhóm phân loại chuẩn"""
    if not raw:
        return "Khác"
    r = raw.strip().lower()
    
    # Check exact match in map
    if r in GENRE_TAXONOMY_MAP:
        return GENRE_TAXONOMY_MAP[r]
    
    # Check sub-words
    for k, v in GENRE_TAXONOMY_MAP.items():
        if k in r:
            return v
            
    return "Khác"


# ─────────────────────────────────────────────────────────────
# 2. BỘ QUY TẮC NHẬN DIỆN THỂ LOẠI & QUỐC GIA CHUYÊN SÂU
# ─────────────────────────────────────────────────────────────
_VN_BOLERO_ARTISTS = {
    "nhu quynh", "như quỳnh", "che linh", "chế linh", "quang le", "quang lê", 
    "truong vu", "trường vũ", "phi nhung", "huong lan", "hương lan", "giao linh", 
    "manh quynh", "mạnh quỳnh", "le quyen", "lệ quyên", "tuan vu", "tuấn vũ", 
    "dan nguyen", "đan nguyên", "ngoc son", "ngọc sơn", "duy khanh", "duy khánh", 
    "thanh tuyen", "thanh tuyền", "hoang oanh", "hoàng oanh", "phuong dung", "phương dung", 
    "mai thien van", "mai thiên vân", "quoc dai", "quốc đại", "cam ly", "cẩm ly", 
    "duong ngoc thai", "dương ngọc thái", "ha thanh xuan", "hà thanh xuân", "to my", "tố my",
    "luu anh loan", "lưu ánh loan", "quynh trang", "quỳnh trang", "huynh nguyen cong sang"
}

_VN_RAP_ARTISTS = {
    "den vau", "đen vâu", "den", "đen", "b ray", "karik", "justatee", "binz", 
    "hieuthuhai", "mck", "wxrdie", "rhymastic", "tage", "bigdaddy", "suboi", 
    "andree", "andree right hand", "low g", "24k.right", "icd", "lk", "phao", "pháo", 
    "gill", "de choat", "dế choắt", "double2t", "tlinh", "16 typh", "sol7", "blacka", 
    "wowy", "duyen quynh", "rap viet", "gducky", "gonzo", "seachains"
}

_VN_ACOUSTIC_CHILL_ARTISTS = {
    "vu.", "vũ.", "vu", "vũ", "chillies", "ngot", "ngọt", "ca hoi hoang", "cá hồi hoang", 
    "trang", "thinh suy", "thịnh suy", "hoang dung", "hoàng dũng", "ha anh tuan", "hà anh tuấn", 
    "kai dinh", "kai đinh", "le cat trong ly", "lê cát trọng lý", "phan manh quynh", "phan mạnh quỳnh", 
    "nguyen ha", "nguyên hà", "thai dinh", "thái đinh", "buitruonglinh", "bùi trường linh", 
    "lyly", "hứa kim tuyền", "hua kim tuyen", "marzuz", "orange", "grey d"
}

_VN_POP_ARTISTS = {
    "son tung m-tp", "sơn tùng m-tp", "son tung", "sơn tùng", "my tam", "mỹ tâm", 
    "ho ngoc ha", "hồ ngọc hà", "dan truong", "đan trường", "cam ly", "cẩm ly", 
    "lam truong", "lam trường", "erik", "duc phuc", "đức phúc", "jack", "jack 97", 
    "j97", "soobin", "soobin hoang son", "noo phuoc thinh", "noo phước thịnh", 
    "dong nhi", "đông nhi", "bao anh", "bảo anh", "min", "amee", "hoa minzy", "hòa minzy", 
    "toc tien", "tóc tiên", "mono", "tang duy tan", "tăng duy tân", "anh tu", "anh tú", 
    "quan a.p", "quân a.p", "vu cat tuong", "vũ cát tường", "trinh thanh binh", "trịnh thăng bình"
}

_KR_ARTISTS = {
    "bts", "blackpink", "iu", "exo", "twice", "newjeans", "stray kids", "bigbang", 
    "snsd", "girls' generation", "red velvet", "seventeen", "ive", "aespa", "taeyeon", 
    "psy", "g-dragon", "nct", "enhypen", "txt", "itzy", "lesserafim", "le sserafim", 
    "shinee", "super junior", "mamamoo", "ateez", "got7", "gfriend", "stayc", "treasure", 
    "nmixx", "day6", "akmu", "baekhyun", "jungkook", "jimin", "zico", "crush", "dean", "riize"
}

_JP_ARTISTS = {
    "utada hikaru", "yoasobi", "kenshi yonezu", "aimer", "radwimps", "one ok rock", 
    "official hige dandism", "x japan", "milet", "ayumi hamasaki", "namie amuro", 
    "king gnu", "ado", "eve", "vocaloid", "hatsune miku", "flow", "sawano hiroyuki", 
    "joe hisaishi", "lisa", "yorushika", "vaundy", "fujii kaze", "mrs. green apple"
}

_CN_ARTISTS = {
    "jay chou", "châu kiệt luân", "faye wong", "vương phi", "jj lin", "lâm tuấn kiệt", 
    "g.e.m", "đặng tử kỳ", "dang tu ky", "ly vinh hao", "lý vinh hạo", "tieu chien", 
    "tiêu chiến", "vuong nhat bac", "vương nhất bác", "truong hoc huu", "trương học hữu", 
    "luu duc hoa", "lưu đức hoa", "quach phu thanh", "quách phú thành", "le minh", "lê minh", 
    "tran dich tan", "trần dịch tấn", "eason chan", "chau tham", "châu thâm", "zhou shen", 
    "phuong hoang truyen ky", "phượng hoàng truyền kỳ", "phoenix legend", "eric chou", "châu hưng triết"
}

_TH_ARTISTS = {
    "jeff satur", "billkin", "pp krit", "nanon", "bright vachirawit", "three man down",
    "tilly birds", "bowkylion", "violette wautier", "milli", "f.hero", "non kul", "the toys",
    "ink waruntorn", "scrubb", "cocktail", "bodyslam", "getsunova", "palmy", "stamp apiwat"
}

_LATIN_ARTISTS = {
    "bad bunny", "daddy yankee", "luis fonsi", "j balvin", "shakira", "rosalia", "rosalía",
    "maluma", "enrique iglesias", "camila cabello", "ozuna", "rauw alejandro", "anuel aa",
    "karol g", "becky g", "ricky martin", "jennifer lopez", "pitbull", "gipsy kings", "alvaro soler"
}

_FR_ARTISTS = {
    "indila", "stromae", "carla bruni", "edith piaf", "alizee", "alizée", "kendji girac",
    "angele", "angèle", "zaz", "gims", "aya nakamura", "claude francois", "charles aznavour"
}


def classify_genre_and_country(
    title: str = "",
    artist: str = "",
    album: str = "",
    raw_genre: str = "",
    file_name: str = "",
    caption: str = "",
    year: str = ""
) -> Dict[str, str]:
    """
    Phân tích thông minh & chuẩn hóa thể loại, quốc gia và thập niên (Era) cho bài hát.
    """
    full_text = f"{title} {artist} {album} {file_name} {caption}".strip()
    low_text = full_text.lower()
    low_art = (artist or "").lower().strip()
    low_title = (title or "").lower().strip()
    low_fn = (file_name or "").lower().strip()

    detected_genre = ""
    detected_country = "Quốc Tế"
    detected_era = "2020s"

    # ── 1. XÁC ĐỊNH QUỐC GIA TRƯỚC (ƯU TIÊN NGHỆ SĨ CHUẨN XÁC) ──
    if any(a in low_art for a in _KR_ARTISTS):
        detected_country = "Hàn Quốc"
    elif any(a in low_art for a in _JP_ARTISTS):
        detected_country = "Nhật Bản"
    elif any(a in low_art for a in _CN_ARTISTS):
        detected_country = "Hoa Ngữ"
    elif any(a in low_art for a in _TH_ARTISTS):
        detected_country = "Thái Lan"
    elif any(a in low_art for a in _LATIN_ARTISTS):
        detected_country = "Latin / Tây Ban Nha"
    elif any(a in low_art for a in _FR_ARTISTS):
        detected_country = "Pháp / Châu Âu"
    elif any(a in low_art for a in _VN_BOLERO_ARTISTS | _VN_RAP_ARTISTS | _VN_ACOUSTIC_CHILL_ARTISTS | _VN_POP_ARTISTS):
        detected_country = "Việt Nam"
    # Ký tự đặc trưng từng ngôn ngữ & chữ viết
    elif re.search(r'[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]', full_text) or any(k in low_art or k in low_text for k in ["k-pop", "kpop", "korean", "ost hàn"]):
        detected_country = "Hàn Quốc"
    elif re.search(r'[\u3040-\u309f\u30a0-\u30ff]', full_text) or any(k in low_art or k in low_text for k in ["j-pop", "jpop", "anime", "japanese"]):
        detected_country = "Nhật Bản"
    elif re.search(r'[\u4e00-\u9fff]', full_text) or any(k in low_art or k in low_text for k in ["c-pop", "cpop", "mandopop", "cantopop", "nhạc hoa", "nhạc trung"]):
        detected_country = "Hoa Ngữ"
    elif re.search(r'[\u0e00-\u0e7f]', full_text) or any(k in low_art or k in low_text for k in ["t-pop", "tpop", "thai pop", "nhạc thái", "ost thái"]):
        detected_country = "Thái Lan"
    # Latin / Tây Ban Nha
    elif any(k in low_art or k in low_text for k in ["latin", "reggaeton", "bachata", "salsa", "despacito", "spanish pop", "musica latina"]):
        detected_country = "Latin / Tây Ban Nha"
    # Pháp / Châu Âu
    elif any(k in low_art or k in low_text for k in ["chanson", "french pop", "nhạc pháp", "lời pháp", "france gall", "french chanson"]):
        detected_country = "Pháp / Châu Âu"
    # Tiếng Việt có dấu
    elif re.search(r'[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ]', full_text):
        detected_country = "Việt Nam"
    elif any(k in low_art or k in low_text for k in ["v-pop", "vpop", "nhạc việt", "nhac viet", "bolero", "trữ tình", "nhạc vàng", "rap việt", "nhạc trẻ"]):
        detected_country = "Việt Nam"
    elif any(k in low_art or k in low_text for k in ["us-uk", "usuk", "taylor swift", "the weeknd", "bruno mars", "adele", "ed sheeran", "coldplay", "maroon 5", "billie eilish", "dua lipa", "queen", "beatles"]):
        detected_country = "Âu Mỹ"
    else:
        detected_country = "Âu Mỹ"

    # ── 2. XÁC ĐỊNH THỂ LOẠI THÔNG MINH (HEURISTICS ĐẶC THÙ) ──
    # A. Bolero / Trữ Tình (Ưu tiên nghệ sĩ & từ khóa)
    if any(a in low_art for a in _VN_BOLERO_ARTISTS) or any(k in low_text for k in ["bolero", "trữ tình", "nhạc vàng", "tân cổ", "liên khúc chiều mưa", "đò nghèo", "áo em chưa mặc", "con đường xưa em đi", "sầu tím", "chuyến tàu hoàng hôn", "thương về miền trung", "vọng cổ", "dân ca"]):
        detected_genre = "Bolero / Trữ Tình"

    # B. EDM / Remix / Vinahouse (Bắt theo từ khóa remix/vinahouse trong tiêu đề & file name)
    elif any(k in low_title or k in low_fn for k in ["remix", "vinahouse", "vina house", "nonstop", "bass boosted", "speed up", "nightcore", "mashup", "club mix", "extended mix", "dj ", "dj-", "electro remix", "house mix", "dance remix", "festival edit"]):
        detected_genre = "EDM / Remix"

    # C. Rap / Hip-Hop
    elif any(a in low_art for a in _VN_RAP_ARTISTS) or any(k in low_text for k in ["rap việt", "rap viet", "freestyle", "cypher", "prod. by", "hip-hop", "hip hop", "diss ", "dissing", "trap beat", "r.a.p"]):
        detected_genre = "Rap / Hip-Hop"

    # D. Acoustic / Chill / Lofi
    elif any(a in low_art for a in _VN_ACOUSTIC_CHILL_ARTISTS) or any(k in low_text for k in ["lofi", "lo-fi", "chill ver", "chill version", "acoustic", "unplugged", "coffee chill", "guitar cover", "piano version", "live session"]):
        detected_genre = "Acoustic / Chill / Lofi"

    # E. Nhạc Đỏ / Cách Mạng
    elif any(k in low_text for k in ["tiền chiến", "cách mạng", "nhạc đỏ", "giải phóng", "trường sơn", "bác hồ", "việt nam quê hương tôi", "bài ca hy vọng", "hành khúc", "đoàn vệ quốc quân", "đất nước trọn niềm vui"]):
        detected_genre = "Nhạc Đỏ / Cách Mạng"

    # F. Nhạc Phim / OST
    elif any(k in low_text for k in [" ost", "ost ", "(ost)", "[ost]", "soundtrack", "nhạc phim", "original soundtrack", "theme song", "opening theme", "ending theme"]):
        detected_genre = "Nhạc Phim / OST"

    # G. Thiếu Nhi / Kids
    elif any(k in low_text for k in ["thiếu nhi", "mầm non", "búp bê", "chú voi con", "cá vàng bơi", "ba ngọn nến", "nursery rhymes"]):
        detected_genre = "Thiếu Nhi / Kids"

    # H. Podcast / Sách Nói
    elif any(k in low_text for k in ["podcast", "sách nói", "audiobook", "truyện đọc", "thiền định", "radio tâm sự"]):
        detected_genre = "Podcast / Sách Nói"

    # I. Nếu chưa có kết quả, dùng raw_genre từ Apple Music / Deezer / Shazam qua GENRE_TAXONOMY_MAP
    if not detected_genre and raw_genre:
        norm = normalize_raw_genre(raw_genre)
        if norm and norm != "Khác":
            detected_genre = norm

    # J. Fallback theo quốc gia nếu vẫn là Khác
    if not detected_genre or detected_genre == "Khác":
        if detected_country == "Việt Nam":
            detected_genre = "V-Pop / Nhạc Trẻ"
        elif detected_country in ["Hàn Quốc", "Hoa Ngữ", "Nhật Bản"]:
            detected_genre = "Pop / Ballad"
        else:
            detected_genre = "Pop / Ballad"

    # Điều chỉnh: Nếu ở Việt Nam và genre là "Pop / Ballad" thì gắn "V-Pop / Nhạc Trẻ"
    if detected_country == "Việt Nam" and detected_genre == "Pop / Ballad":
        detected_genre = "V-Pop / Nhạc Trẻ"

    # ── 3. XÁC ĐỊNH THẬP NIÊN (ERA) ──
    y_int = 0
    if year:
        m_y = re.search(r'\b(19\d{2}|20\d{2})\b', str(year))
        if m_y:
            y_int = int(m_y.group(1))

    if not y_int:
        # Tìm trong text
        m_y2 = re.search(r'\b(19\d{2}|20\d{2})\b', full_text)
        if m_y2:
            y_int = int(m_y2.group(1))

    if y_int > 0:
        if y_int < 1990:
            detected_era = "80s & Trước"
        elif y_int < 2000:
            detected_era = "90s"
        elif y_int < 2010:
            detected_era = "2000s"
        elif y_int < 2020:
            detected_era = "2010s"
        else:
            detected_era = "2020s"
    else:
        detected_era = "2020s"

    return {
        "genre": detected_genre,
        "country": detected_country,
        "era": detected_era
    }


def token_similarity(str1: str, str2: str) -> float:
    """Tính độ tương đồng token giữa 2 chuỗi để chọn kết quả chính xác nhất"""
    if not str1 or not str2:
        return 0.0
    w1 = set(re.findall(r'[a-zA-Z0-9\u00C0-\u1EF9]+', str1.lower()))
    w2 = set(re.findall(r'[a-zA-Z0-9\u00C0-\u1EF9]+', str2.lower()))
    if not w1 or not w2:
        return 0.0
    intersection = w1.intersection(w2)
    return len(intersection) / max(len(w1), len(w2))


def strip_copy_prefix(text: str) -> str:
    """
    Loại bỏ tiền tố sao chép do Google Drive hoặc hệ điều hành tự động thêm vào:
    'Bản sao của ...', 'Bản sao (1) của ...', 'Bản sao ...', 'Copy of ...', 'Copy (1) of ...'
    """
    if not text:
        return ""
    pattern = r'^(?:bản\s*sao(?:\s*\(\d+\))?\s*(?:của)?|copy(?:\s*(?:of|\(\d+\)))?\s*(?:of)?)\s*[:\-–]?\s+'
    res = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
    return res or text


def clean_audio_filename(fn: str) -> str:
    """Làm sạch tên file/tiêu đề, loại bỏ các tag rác Telegram và tiền tố sao chép Google Drive"""
    if not fn:
        return ""
    
    orig_base = re.sub(r'\.(mp3|flac|m4a|wav|aac|ogg|opus|alac|dsf|dff|dsd|ape|wma)$', '', fn, flags=re.IGNORECASE).strip()
    
    # 0. Loại bỏ tiền tố sao chép Google Drive (Bản sao của, Copy of)
    orig_base = strip_copy_prefix(orig_base)
    
    # 1. Bỏ phần mở rộng audio
    res = orig_base
    
    # 2. Bỏ @channel username
    res = re.sub(r'@[^\s_.-]+[_\s.-]*', ' ', res)
    
    # 3. Bỏ nội dung trong ngoặc vuông
    res = re.sub(r'\[.*?\]', ' ', res)
    
    # 4. Bỏ các tag trong ngoặc tròn rác
    res = re.sub(r'\((Official|Lyric|Audio|Visualizer|Remastered|Album Version|Explicit|Video|Bonus|Deluxe|Live|MV|Full MV).*?\)', ' ', res, flags=re.IGNORECASE)
    
    # 5. Bỏ các từ khóa chất lượng
    res = re.sub(r'\b(320kbps|128kbps|256kbps|FLAC|MP3|WAV|DFF|DSF|DSD|24bit|16bit|96kHz|44\.1kHz|Hi-Res|Lossless|Kbps|HQ|HD|4K|1080p)\b', ' ', res, flags=re.IGNORECASE)
    
    # 6. Chuẩn hóa khoảng trắng, dấu chấm, gạch dưới
    res = res.replace('_', ' ')
    res = re.sub(r'\.+', ' ', res)
    res = re.sub(r'\s*-\s*', ' - ', res)
    
    # Nếu bản thân tên file chỉ là số thứ tự thuần túy (ví dụ 01, 12, 1)
    if re.match(r'^\s*\d{1,3}\s*$', res):
        return f"Track {int(res):02d}"

    # 7. Bỏ số thứ tự bài hát ở đầu CHỈ KHI sau đó còn tên bài hát thực sự
    sub_res = re.sub(r'^\s*(\d{1,3}[\.\-_\s]+|\bTrack\s*\d+\b\s*[\.\-_\s]*|[A-D]\d+[\.\-_\s]+)', '', res).strip()
    
    if sub_res and len(sub_res) >= 2 and not re.match(r'^\d+$', sub_res):
        res = sub_res
    else:
        # Nếu sau khi bỏ số thứ tự mà chuỗi trống rỗng (ví dụ tên file chỉ là "Track01", "01"),
        # giữ lại số thứ tự chuẩn để không bị biến thành chuỗi rác "Track"
        m_tr = re.search(r'\bTrack\s*(\d+)\b', res, re.IGNORECASE)
        if m_tr:
            res = f"Track {int(m_tr.group(1)):02d}"
        else:
            m_num = re.search(r'^\s*(\d{1,3})\s*$', orig_base) or re.search(r'^\s*(\d{1,3})\b', res)
            if m_num:
                res = f"Track {int(m_num.group(1)):02d}"
            else:
                res = orig_base or "Track"
    
    res = strip_copy_prefix(res)
    res = re.sub(r'\s+', ' ', res).strip()
    return res


_GARBAGE_KEYWORDS = {
    "admin", "download", "link", "join", "group", "channel", "pass", "password", 
    "zalo", "facebook", "telegram", "bot", "lossless", "flac", "mp3", "wav", 
    "320kbps", "192khz", "24bit", "16bit", "m4a", "dsd", "dsf", "hi-res", "hires",
    "http", "https", "t.me", "fshare", "drive", "youtube", "mediafire", "mega.nz"
}


def _is_valid_name(text: str, max_len: int = 60) -> bool:
    if not text:
        return False
    t = text.strip()
    if len(t) < 2 or len(t) > max_len:
        return False
    if re.search(r'https?://|t\.me/|@[\w_]+|\b(?:fshare|drive\.google|mediafire)\b', t, re.I):
        return False
    words = set(re.findall(r'\b\w+\b', t.lower()))
    if words and words.issubset(_GARBAGE_KEYWORDS):
        return False
    return True


def extract_context_from_text(text: str) -> Tuple[str, str]:
    """
    Trích xuất tên Album và Ca Sĩ từ tin nhắn văn bản / caption một cách an toàn và nghiêm ngặt (Strict).
    Tự động loại bỏ tiền tố sao chép từ Google Drive (Bản sao của, Copy of).
    """
    if not text:
        return "", ""
    
    clean = re.sub(r'https?://\S+|t\.me/\S+|@[\w_]+|#\w+', '', text).strip()
    clean = strip_copy_prefix(clean)
    if not clean:
        return "", ""

    artist = ""
    album = ""

    artist_labels = r'Ca\s*s[ĩỹi]|Ngh[eệ]\s*s[ĩi]|Tr[iì]nh\s*b[aà]y|Artist|Singer|Performer'
    m_artist = re.search(rf'(?:{artist_labels})\s*[:\-–]\s*([^\n\r,;\|]+)', clean, re.IGNORECASE)
    if m_artist:
        candidate_artist = strip_copy_prefix(m_artist.group(1).strip())
        if _is_valid_name(candidate_artist, 50):
            artist = candidate_artist

    album_labels = r'Album|CD\s*\d*|Tuy[eể]n\s*t[aậ]p|[ĐD][ĩi]a\s*h[aá]t|Collection|Nh[aạ]c\s*tuy[eể]n'
    m_album = re.search(rf'(?:{album_labels})\s*[:\-–]\s*([^\n\r,;\|]+)', clean, re.IGNORECASE)
    if m_album:
        candidate_album = strip_copy_prefix(m_album.group(1).strip())
        if _is_valid_name(candidate_album, 60):
            album = candidate_album

    if not artist or not album:
        lines = [line.strip() for line in clean.split('\n') if line.strip()]
        if lines:
            first_line = lines[0]
            if len(first_line) <= 80:
                first_line = strip_copy_prefix(first_line)
                first_line = re.sub(r'^[^\w\s\u00C0-\u1EF9]+', '', first_line).strip()
                first_line = re.sub(r'\[.*?\]', '', first_line).strip()
                first_line = re.sub(r'\((?:19|20)\d{2}\)', '', first_line).strip()

                for sep in [' - ', ' – ', ' — ']:
                    if sep in first_line:
                        parts = first_line.split(sep)
                        if len(parts) >= 2:
                            p_art = strip_copy_prefix(parts[0].strip())
                            p_alb = strip_copy_prefix(parts[1].strip())
                            if not artist and _is_valid_name(p_art, 50):
                                artist = p_art
                            if not album and _is_valid_name(p_alb, 60):
                                album = p_alb
                        break

    return artist, album


def parse_artist_and_title(raw_title: str = "", raw_artist: str = "", raw_album: str = "", file_name: str = "", caption: str = "") -> Tuple[str, str, str]:
    """
    Trích xuất Artist, Title, Album ưu tiên dữ liệu gốc từ ID3 tag và File Name.
    """
    clean_fn = clean_audio_filename(file_name)
    clean_cap = clean_audio_filename(caption)
    clean_title = clean_audio_filename(raw_title)
    clean_artist = clean_audio_filename(raw_artist)
    
    def _strip_track_number(s: str) -> str:
        s = re.sub(r'^(?:\[?\d{1,3}\]?[\s.\-_–]+)', '', s).strip()
        return s

    if clean_title:
        clean_title = _strip_track_number(clean_title)
    if clean_fn:
        clean_fn = _strip_track_number(clean_fn)

    if clean_artist and ('@' in clean_artist or clean_artist.lower() in ["unknown artist", "unknown", "va", "various artists", "telegram", "lossless"]):
        clean_artist = ""

    if clean_artist and clean_title and clean_title.lower() != clean_artist.lower():
        return clean_artist, clean_title, raw_album or ""

    target_str = clean_fn or clean_cap or clean_title
    for sep in [' - ', ' – ', ' — ']:
        if sep in target_str:
            parts = target_str.split(sep)
            if len(parts) == 2:
                part1 = _strip_track_number(parts[0].strip())
                part2 = _strip_track_number(parts[1].strip())
                artist = clean_artist or part1
                title = part2 if clean_artist else part2
                return artist, title, raw_album or ""
            elif len(parts) >= 3:
                p_art = _strip_track_number(parts[0].strip())
                p_alb = parts[1].strip()
                p_tit = _strip_track_number(parts[-1].strip())
                return clean_artist or p_art, p_tit, raw_album or p_alb

    artist = clean_artist or ""
    title = clean_title or clean_fn or clean_cap or "Track"
    return artist, title, raw_album or ""


def is_generic_music_query(title: str, artist: str = "") -> bool:
    """Kiểm tra xem tên bài hát / nghệ sĩ có phải là chuỗi chung chung không có giá trị tìm kiếm trực tuyến hay không."""
    if not title:
        return True
    t = title.strip().lower()
    a = (artist or "").strip().lower()
    
    # Nếu có nghệ sĩ rõ ràng và hợp lệ (không phải unknown/va)
    has_valid_artist = bool(a and a not in [
        "unknown artist", "unknown", "va", "various artists", "various", "ca sĩ", "telegram", "lossless", "admin"
    ])
    
    # Các mẫu tên file chỉ là số thứ tự hoặc từ khóa chung chung
    generic_patterns = [
        r'^(track|audio|bai|bai hat|cd|disc|soundtrack|song)?\s*\d*$',
        r'^\d+$',
        r'^[a-d]\d+$'
    ]
    is_pattern_generic = any(re.match(p, t) for p in generic_patterns)
    
    # Nếu chỉ là dạng "Track 01", "01" thì luôn là generic
    if is_pattern_generic:
        return True
        
    if not has_valid_artist:
        if t in ["track", "audio", "unknown", "untitled", "music", "song", "audio track", "cd track", "noname", "soundtrack"]:
            return True
        if len(t) < 3:
            return True

    return False


async def _search_deezer(query: str, orig_title: str = "", orig_artist: str = "") -> Optional[dict]:
    """Tìm kiếm metadata dự phòng từ Deezer API khi iTunes không có kết quả với kiểm tra độ tương đồng nghiêm ngặt"""
    if not query:
        return None
    try:
        url = f"https://api.deezer.com/search?q={urllib.parse.quote(query)}&limit=5"
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                data = resp.json()
                tracks = data.get("data", [])
                best_cand = None
                best_score = 0.0

                for item in tracks:
                    cand_title = item.get("title", "")
                    cand_artist = item.get("artist", {}).get("name", "")
                    cand_album = item.get("album", {}).get("title", "")
                    cand_cover = item.get("album", {}).get("cover_xl") or item.get("album", {}).get("cover_big", "")
                    
                    score_full = token_similarity(query, f"{cand_artist} {cand_title}")
                    score_title = token_similarity(orig_title or query, cand_title)
                    
                    if orig_artist:
                        score_art = token_similarity(orig_artist, cand_artist)
                        if score_art < 0.35 and orig_artist.lower() not in cand_artist.lower() and cand_artist.lower() not in orig_artist.lower():
                            continue
                        cur_score = max(score_full, (score_title * 0.6 + score_art * 0.4))
                    else:
                        cur_score = max(score_full, score_title)

                    if cur_score > best_score:
                        best_score = cur_score
                        best_cand = {
                            "title": cand_title,
                            "artist": cand_artist,
                            "album": cand_album or f"{cand_title} - Single",
                            "cover_url": cand_cover,
                            "year": time.strftime("%Y") if "time" in globals() else "2026",
                            "genre": "Pop / Ballad",
                            "publisher": f"{cand_artist} / Deezer",
                            "source": "Deezer API",
                            "score": cur_score
                        }

                # Chỉ chấp nhận nếu độ tương đồng tối thiểu >= 0.45
                if best_cand and best_score >= 0.45:
                    return best_cand
                elif best_cand:
                    LOGGER.debug(f"[DEEZER] Bỏ qua kết quả '{best_cand['artist']} - {best_cand['title']}' do tương đồng thấp ({best_score:.2f} < 0.45)")
    except Exception as e:
        LOGGER.debug(f"[MUSIC SCRAPER] Deezer fallback query failed for '{query}': {e}")
    return None


async def fetch_music_metadata(
    raw_title: str = "", 
    raw_artist: str = "", 
    raw_album: str = "", 
    file_name: str = "", 
    caption: str = "", 
    default_artist: str = "", 
    default_album: str = ""
) -> Optional[dict]:
    """
    Tự động nhận diện chính xác bài hát & Album từ Apple Music / iTunes API & Deezer API,
    kết hợp bộ chuẩn hóa thể loại (Taxonomy Engine) và phân loại quốc gia, thập niên.
    """
    artist, title, album_hint = parse_artist_and_title(raw_title, raw_artist or default_artist, raw_album or default_album, file_name, caption)
    
    if not title:
        return None

    if default_artist and (not artist or artist.lower() in ["unknown artist", "unknown"]):
        artist = default_artist

    if default_album and (not album_hint or album_hint.lower() in ["telegram music collection"]):
        album_hint = default_album

    # Bỏ qua tìm kiếm trực tuyến nếu tên bài hát là chuỗi chung chung vô danh (Track 01, Audio, v.v.)
    if is_generic_music_query(title, artist):
        LOGGER.info(f"[MUSIC SCRAPER] Tiêu đề '{title}' (Artist: '{artist or 'None'}') là tên tệp chung chung/vô danh, bỏ qua tìm kiếm trực tuyến để tránh nhận diện sai.")
        return None

    search_query = f"{artist} {title}".strip() if artist else title
    cache_key = search_query.lower()
    if cache_key in _METADATA_CACHE:
        return _METADATA_CACHE[cache_key]

    LOGGER.info(f"[MUSIC SCRAPER] Đang tìm metadata cho: '{search_query}' (Gốc: '{file_name or raw_title}')...")

    # 1. Tìm kiếm trên Apple Music / iTunes API
    candidates: List[dict] = []
    queries_to_try = [search_query]
    if artist and title:
        inverted = f"{title} {artist}".strip()
        if inverted not in queries_to_try:
            queries_to_try.append(inverted)
        if title not in queries_to_try:
            queries_to_try.append(title)

    for q in queries_to_try:
        try:
            url = f"https://itunes.apple.com/search?term={urllib.parse.quote(q)}&entity=song&limit=5"
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("results", []):
                        cand_title = item.get("trackName", "")
                        cand_artist = item.get("artistName", "")
                        cand_album = item.get("collectionName", "")
                        
                        score_full = token_similarity(search_query, f"{cand_artist} {cand_title}")
                        score_title = token_similarity(title, cand_title)
                        
                        match_fwd = (token_similarity(artist, cand_artist) * 0.5 + token_similarity(title, cand_title) * 0.5) if (artist and title) else 0.0
                        match_rev = (token_similarity(artist, cand_title) * 0.5 + token_similarity(title, cand_artist) * 0.5) if (artist and title) else 0.0
                        
                        final_score = max(score_full, score_title * 0.8, match_fwd, match_rev)
                        full_raw_text = (file_name + ' ' + caption + ' ' + raw_title + ' ' + raw_artist).lower()
                        
                        if cand_title.lower() in full_raw_text and cand_artist.lower() in full_raw_text:
                            final_score = max(final_score, 0.95)
                        elif cand_artist.lower() in full_raw_text:
                            final_score = max(final_score, 0.85)
                        elif not artist:
                            if cand_artist.lower() not in full_raw_text:
                                continue
                        else:
                            artist_score_fwd = token_similarity(artist, cand_artist)
                            artist_score_rev = token_similarity(title, cand_artist)
                            if max(artist_score_fwd, artist_score_rev) < 0.35 and cand_artist.lower() not in full_raw_text:
                                continue

                            final_score = min(1.0, final_score + 0.25)

                        raw_art = item.get("artworkUrl100", "")
                        hd_cover = raw_art.replace("100x100bb.jpg", "1200x1200bb.webp").replace("100x100bb.png", "1200x1200bb.webp")
                        release_date = item.get("releaseDate", "")
                        year = release_date[:4] if len(release_date) >= 4 else "2026"
                        raw_genre = item.get("primaryGenreName", "")

                        # Phân loại chuyên sâu bằng classifier
                        cls_meta = classify_genre_and_country(
                            title=cand_title,
                            artist=cand_artist,
                            album=cand_album,
                            raw_genre=raw_genre,
                            file_name=file_name,
                            caption=caption,
                            year=year
                        )

                        candidates.append({
                            "score": final_score,
                            "title": cand_title,
                            "artist": cand_artist,
                            "album": cand_album or f"{cand_title} - Single",
                            "cover_url": hd_cover or raw_art,
                            "year": year,
                            "genre": cls_meta["genre"],
                            "country": cls_meta["country"],
                            "era": cls_meta["era"],
                            "publisher": f"{cand_artist} / Apple Music",
                            "source": "Apple Music / iTunes",
                            "layer": "Apple Music"
                        })
            if candidates:
                break
        except Exception as e:
            LOGGER.warning(f"[MUSIC SCRAPER] iTunes search failed for '{q}': {e}")

    # 2. Nếu tìm thấy candidate hợp lệ từ iTunes (Điểm >= 0.50)
    if candidates:
        candidates.sort(key=lambda x: x["score"], reverse=True)
        best = candidates[0]
        if best["score"] >= 0.50:
            _METADATA_CACHE[cache_key] = best
            LOGGER.info(f"[MUSIC SCRAPER] ✅ Khớp chính xác: {best['artist']} - {best['title']} [{best['genre']} | {best['country']}]")
            return best

    # 3. Fallback Deezer API
    deezer_res = await _search_deezer(search_query, orig_title=title, orig_artist=artist)
    if deezer_res:
        cls_meta = classify_genre_and_country(
            title=deezer_res["title"],
            artist=deezer_res["artist"],
            album=deezer_res["album"],
            raw_genre=deezer_res.get("genre", ""),
            file_name=file_name,
            caption=caption
        )
        deezer_res["genre"] = cls_meta["genre"]
        deezer_res["country"] = cls_meta["country"]
        deezer_res["era"] = cls_meta["era"]
        deezer_res["layer"] = "Deezer API"
        _METADATA_CACHE[cache_key] = deezer_res
        LOGGER.info(f"[MUSIC SCRAPER] ✅ Khớp từ Deezer: {deezer_res['artist']} - {deezer_res['title']} [{deezer_res['genre']}]")
        return deezer_res

    # 4. Fallback an toàn & phân loại trực tiếp từ thông tin file gốc
    cls_fallback = classify_genre_and_country(
        title=title,
        artist=artist,
        album=album_hint,
        file_name=file_name,
        caption=caption
    )

    fallback_res = {
        "title": title,
        "artist": artist or "Unknown Artist",
        "album": album_hint or "Telegram Music Collection",
        "cover_url": "",
        "year": "2026",
        "genre": cls_fallback["genre"],
        "country": cls_fallback["country"],
        "era": cls_fallback["era"],
        "publisher": "Telegram Cloud Archive",
        "source": "Telegram Direct",
        "layer": "Tệp Gốc"
    }
    _METADATA_CACHE[cache_key] = fallback_res
    return fallback_res


async def fetch_album_tracklist_online(album_name: str, artist_name: str = "") -> Dict[int, dict]:
    """
    Tra cứu danh sách toàn bộ bài hát (Tracklist) của một Album từ Apple Music / iTunes và Deezer.
    Trả về Dict: {track_number: {"title": str, "artist": str, "album": str, "cover_url": str}}
    """
    if not album_name:
        return {}

    clean_alb = strip_copy_prefix(album_name).strip()
    clean_art = strip_copy_prefix(artist_name).strip()
    if not clean_alb:
        return {}

    tracks_map: Dict[int, dict] = {}
    query = f"{clean_art} {clean_alb}".strip() if clean_art else clean_alb

    # 1. Thử iTunes API (ưu tiên catalog VN, sau đó fallback sang US)
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            for country in ["VN", "US"]:
                url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=album&country={country}&limit=6"
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    continue
                data = resp.json()
                results = data.get("results", [])
                if not results:
                    continue

                best_col = None
                target_clean = re.sub(r'[^a-zA-Z0-9\u00C0-\u1EF9]', '', clean_alb.lower())
                target_num = re.search(r'\d+', clean_alb)

                # Ưu tiên 1: Khớp chính xác tuyệt đối tên album
                for col in results:
                    c_name = col.get("collectionName", "")
                    c_clean = re.sub(r'[^a-zA-Z0-9\u00C0-\u1EF9]', '', c_name.lower())
                    if target_clean == c_clean:
                        best_col = col
                        break

                # Ưu tiên 2: Khớp số thứ tự tập/album (ví dụ: Khúc Tình Xưa 6 khớp album có số 6)
                if not best_col and target_num:
                    for col in results:
                        c_name = col.get("collectionName", "")
                        c_num = re.search(r'\d+', c_name)
                        if c_num and c_num.group(0) == target_num.group(0):
                            best_col = col
                            break

                # Ưu tiên 3: Chuỗi con tương đồng
                if not best_col:
                    for col in results:
                        c_name = col.get("collectionName", "")
                        c_clean = re.sub(r'[^a-zA-Z0-9\u00C0-\u1EF9]', '', c_name.lower())
                        if target_clean in c_clean or c_clean in target_clean:
                            best_col = col
                            break

                if not best_col and results:
                    best_col = results[0]

                if best_col:
                    cid = best_col.get("collectionId")
                    raw_cover = best_col.get("artworkUrl100", "")
                    cover_url = raw_cover.replace("100x100bb", "600x600bb") if raw_cover else ""
                    lookup_url = f"https://itunes.apple.com/lookup?id={cid}&entity=song&country={country}"
                    l_resp = await client.get(lookup_url, headers={"User-Agent": "Mozilla/5.0"})
                    if l_resp.status_code == 200:
                        l_data = l_resp.json()
                        for item in l_data.get("results", []):
                            if item.get("wrapperType") == "track":
                                t_num = item.get("trackNumber")
                                t_name = item.get("trackName")
                                if t_num and t_name:
                                    tracks_map[int(t_num)] = {
                                        "title": t_name,
                                        "artist": item.get("artistName", clean_art),
                                        "album": best_col.get("collectionName", clean_alb),
                                        "cover_url": cover_url
                                    }
                        if tracks_map:
                            LOGGER.info(f"[ALBUM TRACKLIST] Đã khớp {len(tracks_map)} bài cho album '{clean_alb}' từ iTunes ({country})")
                            return tracks_map
    except Exception as e:
        LOGGER.debug(f"[ALBUM TRACKLIST] iTunes search error: {e}")

    # 2. Fallback sang Deezer API nếu iTunes chưa tìm thấy
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            d_url = f"https://api.deezer.com/search/album?q={urllib.parse.quote(query)}&limit=5"
            d_resp = await client.get(d_url, headers={"User-Agent": "Mozilla/5.0"})
            if d_resp.status_code == 200:
                d_data = d_resp.json()
                albums = d_data.get("data", [])
                best_alb = None
                target_clean = re.sub(r'[^a-zA-Z0-9\u00C0-\u1EF9]', '', clean_alb.lower())
                target_num = re.search(r'\d+', clean_alb)
                for alb in albums:
                    a_title = alb.get("title", "")
                    a_clean = re.sub(r'[^a-zA-Z0-9\u00C0-\u1EF9]', '', a_title.lower())
                    if target_clean == a_clean:
                        best_alb = alb
                        break
                if not best_alb and target_num:
                    for alb in albums:
                        a_title = alb.get("title", "")
                        a_num = re.search(r'\d+', a_title)
                        if a_num and a_num.group(0) == target_num.group(0):
                            best_alb = alb
                            break
                if not best_alb and albums:
                    best_alb = albums[0]

                if best_alb:
                    alb_id = best_alb.get("id")
                    cover_url = best_alb.get("cover_xl") or best_alb.get("cover_big") or best_alb.get("cover_medium", "")
                    t_url = f"https://api.deezer.com/album/{alb_id}/tracks?limit=50"
                    t_resp = await client.get(t_url, headers={"User-Agent": "Mozilla/5.0"})
                    if t_resp.status_code == 200:
                        t_data = t_resp.json()
                        for idx, track_item in enumerate(t_data.get("data", []), start=1):
                            t_num = track_item.get("track_position") or idx
                            t_title = track_item.get("title") or track_item.get("title_short")
                            art_name = track_item.get("artist", {}).get("name") or clean_art
                            if t_title:
                                tracks_map[int(t_num)] = {
                                    "title": t_title,
                                    "artist": art_name,
                                    "album": best_alb.get("title", clean_alb),
                                    "cover_url": cover_url
                                }
                        if tracks_map:
                            LOGGER.info(f"[ALBUM TRACKLIST] Đã khớp {len(tracks_map)} bài cho album '{clean_alb}' từ Deezer")
                            return tracks_map
    except Exception as e:
        LOGGER.debug(f"[ALBUM TRACKLIST] Deezer search error: {e}")

    return tracks_map
