from flask import Flask, render_template, request, jsonify
import requests
import json
import os
from urllib.parse import unquote
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)

RAKUTEN_APP_ID = "1077795699367532233"
CALIL_APP_KEY = "a4803b22ab1cf9bd6eda17b6518ea542"
DATA_FILE = "data/shelves.json"

# -----------------------------
# 棚の種類
# -----------------------------
SHELVES = [
    "貯蓄優先型",
    "積立安定型",
    "アクティブチャレンジ型",
    "ステーキング運用型",
    "株式アクティブ型",
    "ハイリスクハイリターン型",
    "テクノロジー志向型",
    "積立応用型",
    "私の本棚",
]

# -----------------------------
# JSON読み書き関数
# -----------------------------
def load_shelves():
    if not os.path.exists(DATA_FILE):
        data = {shelf: [] for shelf in SHELVES}
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_shelves(shelves):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(shelves, f, ensure_ascii=False, indent=2)


# -----------------------------
# Open Library API検索
# -----------------------------
def search_openlibrary(title):
    url = "https://openlibrary.org/search.json"
    params = {"title": title}
    response = requests.get(url, params=params)
    data = response.json()

    books = []
    for doc in data.get("docs", []):
        isbn = doc.get("isbn", [None])[0]
        books.append(
            {
                "title": doc.get("title", ""),
                "author": ", ".join(doc.get("author_name", [])),
                "isbn": isbn,
                "year": doc.get("first_publish_year", ""),
                "cover": f"https://covers.openlibrary.org/b/id/{doc.get('cover_i', 0)}-L.jpg"
                if doc.get("cover_i")
                else "",
                "url": f"https://openlibrary.org{doc.get('key')}",
            }
        )
    return books


# -----------------------------
# カーリルAPI - 近隣図書館検索
# -----------------------------
def find_nearby_libraries(lat, lon):
    url = "https://api.calil.jp/library"
    params = {
        "appkey": CALIL_APP_KEY,
        "geocode": f"{lon},{lat}",  # 経度,緯度
        "format": "json",
        "callback": "",
    }
    response = requests.get(url, params=params)
    try:
        libraries = response.json()
    except json.JSONDecodeError:
        libraries = []
    return libraries[:5]


# -----------------------------
# 距離計算
# -----------------------------
def calc_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


# -----------------------------
# 本検索API（改良版）
# -----------------------------
@app.route("/search")
def search_books():
    title = request.args.get("title", "")
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    if not title:
        return jsonify([])

    # 1. 楽天
    url = "https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "title": title,
        "format": "json",
        "hits": 20,
    }
    response = requests.get(url, params=params)
    data = response.json()

    books = []
    for item in data.get("Items", []):
        book_item = item["Item"]
        books.append(
            {
                "title": book_item.get("title", ""),
                "author": book_item.get("author", ""),
                "isbn": book_item.get("isbn", ""),
                "price": book_item.get("itemPrice", 0),
                "image": book_item.get("largeImageUrl", ""),
                "itemUrl": book_item.get("itemUrl", ""),
                "libraries": [],
            }
        )

    # 2. Open Library
    if not books:
        books = search_openlibrary(title)
        for b in books:
            b["libraries"] = []

    # 3. 図書館情報
    if lat and lon:
        user_lat, user_lon = float(lat), float(lon)
        libraries = find_nearby_libraries(user_lat, user_lon)

        for book in books:
            isbn = book.get("isbn")
            book["libraries"] = []
            for lib in libraries:
                # 緯度経度を追加
                try:
                    lib_lat, lib_lon = map(
                        float, lib.get("geocode", "0,0").split(",")[::-1]
                    )
                except:
                    lib_lat, lib_lon = None, None

                book["libraries"].append(
                    {
                        "name": lib.get("formal"),
                        "lat": lib_lat,
                        "lon": lib_lon,
                        "url": f"https://calil.jp/library/{lib.get('systemid')}",  # リーカル公式リンク
                        "distance": None,  # JS 側で計算
                    }
                )

    return jsonify(books)


# -----------------------------
# トップページ
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html", shelves=SHELVES)


# -----------------------------
# 「私の本棚」関連
# -----------------------------
@app.route("/add_to_my_shelf", methods=["POST"])
def add_to_my_shelf():
    book = request.get_json().get("book")
    if not book:
        return jsonify({"error": "bookが指定されていません"}), 400
    shelves = load_shelves()
    if "私の本棚" not in shelves:
        shelves["私の本棚"] = []
    if not any(b["title"] == book["title"] for b in shelves["私の本棚"]):
        shelves["私の本棚"].append(book)
        save_shelves(shelves)
    return jsonify({"my_shelf": shelves["私の本棚"]})


@app.route("/remove_from_my_shelf", methods=["POST"])
def remove_from_my_shelf():
    title = request.get_json().get("title")
    if not title:
        return jsonify({"error": "titleが指定されていません"}), 400
    shelves = load_shelves()
    shelves["私の本棚"] = [b for b in shelves.get("私の本棚", []) if b["title"] != title]
    save_shelves(shelves)
    return jsonify({"my_shelf": shelves["私の本棚"]})


@app.route("/get_my_shelf")
def get_my_shelf():
    shelves = load_shelves()
    return jsonify({"my_shelf": shelves.get("私の本棚", [])})


@app.route("/shelf/<path:shelf_name>")
def shelf_page(shelf_name):
    shelf_name = unquote(shelf_name)
    shelves = load_shelves()
    books = shelves.get(shelf_name, [])
    my_shelf_books = shelves.get("私の本棚", [])
    return render_template(
        "shelf.html", shelf_name=shelf_name, books=books, my_shelf=my_shelf_books
    )


# -----------------------------
# 実行
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
