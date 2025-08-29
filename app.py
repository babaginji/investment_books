from flask import Flask, render_template, request, jsonify
import requests
import json

app = Flask(__name__)

# 楽天API設定
RAKUTEN_APP_ID = "1077795699367532233"

# 投資タイプとキーワードルール
KEYWORDS = {
    "積立安定型": ["インデックス", "積立", "ETF"],
    "ステーキング運用型": ["ステーキング", "暗号資産", "仮想通貨"],
    "アクティブチャレンジ型": ["短期売買", "トレード", "デイトレ"],
    "株式アクティブ型": ["個別株", "株式投資"],
    "ハイリスクハイリターン型": ["仮想通貨", "高リスク"],
    "テクノロジー志向型": ["ブロックチェーン", "NFT", "Web3"],
    "積立応用型": ["高配当株", "配当投資"],
    "貯蓄優先型": ["貯蓄", "資産運用"],
}

# 本の手動タグデータをロード（例: data/books.json）
try:
    with open("data/books.json", "r", encoding="utf-8") as f:
        MANUAL_TAGS = json.load(f)  # {"本タイトル": "投資タイプ"}
except FileNotFoundError:
    MANUAL_TAGS = {}

# キーワードルールで分類
def classify_book(title, description):
    # 手動タグがあればそれを優先
    if title in MANUAL_TAGS:
        return MANUAL_TAGS[title]

    # キーワードルールで分類
    for book_type, words in KEYWORDS.items():
        if description:
            for word in words:
                if word in description or word in title:
                    return book_type
    return "未分類"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():
    title = request.args.get("title", "")
    url = "https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "title": title,
        "format": "json",
        "hits": 5,
    }
    response = requests.get(url, params=params)
    data = response.json()

    books = []
    for item in data.get("Items", []):
        book_item = item["Item"]
        book_type = classify_book(
            book_item.get("title", ""), book_item.get("itemCaption", "")
        )
        books.append(
            {
                "title": book_item.get("title", ""),
                "author": book_item.get("author", ""),
                "price": book_item.get("itemPrice", ""),
                "image": book_item.get("largeImageUrl", ""),
                "description": book_item.get("itemCaption", ""),
                "type": book_type,
            }
        )
    return jsonify(books)


if __name__ == "__main__":
    app.run(debug=True)
