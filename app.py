from flask import Flask, render_template, request, jsonify
import requests
import json
import os
from urllib.parse import unquote

app = Flask(__name__)

RAKUTEN_APP_ID = "1077795699367532233"
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
        # 初回作成: 空のリストで初期化
        data = {shelf: [] for shelf in SHELVES}
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_shelves(shelves):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(shelves, f, ensure_ascii=False, indent=2)


# -----------------------------
# トップページ
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html", shelves=SHELVES)


# -----------------------------
# 楽天書籍検索API
# -----------------------------
@app.route("/search")
def search_books():
    title = request.args.get("title", "")
    if not title:
        return jsonify([])

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
                "price": book_item.get("itemPrice", 0),
                "image": book_item.get("largeImageUrl", ""),
                "description": book_item.get("itemCaption", ""),
                "itemUrl": book_item.get("itemUrl", ""),
            }
        )
    return jsonify(books)


# -----------------------------
# 「私の本棚」に追加
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


# -----------------------------
# 「私の本棚」から削除
# -----------------------------
@app.route("/remove_from_my_shelf", methods=["POST"])
def remove_from_my_shelf():
    title = request.get_json().get("title")
    if not title:
        return jsonify({"error": "titleが指定されていません"}), 400

    shelves = load_shelves()
    shelves["私の本棚"] = [b for b in shelves.get("私の本棚", []) if b["title"] != title]
    save_shelves(shelves)
    return jsonify({"my_shelf": shelves["私の本棚"]})


# -----------------------------
# 「私の本棚」取得
# -----------------------------
@app.route("/get_my_shelf")
def get_my_shelf():
    shelves = load_shelves()
    return jsonify({"my_shelf": shelves.get("私の本棚", [])})


# -----------------------------
# 各棚ページ
# -----------------------------
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
