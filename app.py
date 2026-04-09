from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from datetime import datetime
from config import MONGO_URI, DB_NAME

import logging
import os

app = Flask(__name__)

# =========================
# ✅ LOGGER SETUP
# =========================
TEST_LOG = os.getenv("TEST_LOG", "false").lower() == "true"

logger = logging.getLogger("app_logger")

if TEST_LOG:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    logger.info("✅ Logging Enabled")
else:
    logging.basicConfig(level=logging.CRITICAL)


# MongoDB Connection
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db["daily_entries"]


# 🏠 Home - View by Date (WITH PAGINATION ADDED)
@app.route("/", methods=["GET", "POST"])
def index():
    try:
        selected_date = request.args.get("date")

        # pagination inputs
        limit = int(request.args.get("limit", 50))
        page = int(request.args.get("page", 1))
        skip = (page - 1) * limit

        data = []
        total = 0

        if selected_date:
            query = {"date": selected_date}

            total = collection.count_documents(query)

            data = list(
                collection.find(query)
                .sort("created_at", -1)
                .skip(skip)
                .limit(limit)
            )

        next_page = page + 1 if (skip + limit) < total else None
        prev_page = page - 1 if page > 1 else None

        if TEST_LOG:
            logger.info(f"Index Loaded | date={selected_date} | page={page} | limit={limit}")

        return render_template(
            "index.html",
            data=data,
            selected_date=selected_date,
            limit=limit,
            next_page=next_page,
            prev_page=prev_page
        )

    except Exception as e:
        logger.exception("❌ Error in index()")
        return "Internal Server Error", 500


# =========================
# ✅ INLINE UPDATE
# =========================
@app.route("/update/<id>", methods=["POST"])
def update_entry(id):
    try:
        from bson import ObjectId
        from flask import jsonify

        data = request.get_json()

        collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "name": data.get("name"),
                "price": float(data.get("price"))
            }}
        )

        if TEST_LOG:
            logger.info(f"Updated Entry | id={id}")

        return jsonify({"success": True})

    except Exception as e:
        logger.exception("❌ Error in update_entry()")
        return jsonify({"success": False, "error": str(e)}), 500


# ➕ Add Entry
@app.route("/add", methods=["GET", "POST"])
def add_entry():
    try:
        if request.method == "POST":
            date = request.form["date"]
            entry_type = request.form["type"]

            health = request.form.get("health")
            if health == "other":
                health = request.form.get("health_custom")

            category = request.form.get("category")
            if category == "other":
                category = request.form.get("category_custom")

            if entry_type == "other":
                entry_type = request.form.get("type_custom")

            if entry_type == "food":
                category = None
            if entry_type == "expense":
                health = None

            entry = {
                "date": date,
                "type": entry_type,
                "category": category,
                "name": request.form["name"],
                "health": health,
                "price": float(request.form["price"]),
                "created_at": datetime.now()
            }

            collection.insert_one(entry)

            if TEST_LOG:
                logger.info(f"Added Entry | date={date} | type={entry_type}")

            return redirect(url_for("index", date=date))

        return render_template("add_entry.html")

    except Exception as e:
        logger.exception("❌ Error in add_entry()")
        return "Internal Server Error", 500


# ✏️ EDIT ENTRY
@app.route("/edit/<id>", methods=["GET", "POST"])
def edit_entry(id):
    try:
        from bson import ObjectId

        entry = collection.find_one({"_id": ObjectId(id)})

        if request.method == "POST":
            updated_data = {
                "name": request.form["name"],
                "price": float(request.form["price"])
            }

            collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": updated_data}
            )

            if TEST_LOG:
                logger.info(f"Edited Entry | id={id}")

            return redirect(url_for("index", date=entry["date"]))

        return render_template("edit.html", entry=entry)

    except Exception as e:
        logger.exception("❌ Error in edit_entry()")
        return "Internal Server Error", 500


# ❌ Delete Entry
@app.route("/delete/<id>")
def delete_entry(id):
    try:
        from bson import ObjectId

        collection.delete_one({"_id": ObjectId(id)})

        if TEST_LOG:
            logger.info(f"Deleted Entry | id={id}")

        return redirect(request.referrer)

    except Exception as e:
        logger.exception("❌ Error in delete_entry()")
        return "Internal Server Error", 500


# ▶️ Run App
if __name__ == "__main__":
    app.run(debug=True)