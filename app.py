import os
import uuid
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    send_from_directory,
)
from werkzeug.utils import secure_filename

import config
from database import get_db, init_db

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH

os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(config.UPLOAD_FOLDER, "thumbnails"), exist_ok=True)


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == config.SITE_PASSWORD:
            session["logged_in"] = True
            session.permanent = True
            return redirect(url_for("landing"))
        flash("Wrong password, try again 💔")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------------------------------------------------------------
# Pages
# ------------------------------------------------------------------

@app.route("/")
@login_required
def landing():
    db = get_db()
    memory_count = db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    letter_count = db.execute("SELECT COUNT(*) FROM letters").fetchone()[0]

    # Get a random featured photo
    featured = db.execute(
        "SELECT * FROM memories WHERE media_type='image' ORDER BY RANDOM() LIMIT 1"
    ).fetchone()

    start = datetime.strptime(config.RELATIONSHIP_START, "%Y-%m-%d").date()
    days_together = (date.today() - start).days

    db.close()
    return render_template(
        "landing.html",
        partner1=config.PARTNER_1,
        partner2=config.PARTNER_2,
        days_together=days_together,
        start_date=config.RELATIONSHIP_START,
        memory_count=memory_count,
        letter_count=letter_count,
        featured=featured,
    )


@app.route("/timeline")
@login_required
def timeline():
    db = get_db()
    memories = db.execute("""
        SELECT m.*, c.name as category_name, c.emoji as category_emoji
        FROM memories m
        LEFT JOIN categories c ON m.category_id = c.id
        ORDER BY m.memory_date DESC, m.created_at DESC
    """).fetchall()
    db.close()
    return render_template("timeline.html", memories=memories)


@app.route("/albums")
@app.route("/albums/<int:category_id>")
@login_required
def albums(category_id=None):
    db = get_db()
    categories = db.execute(
        "SELECT c.*, COUNT(m.id) as count FROM categories c "
        "LEFT JOIN memories m ON m.category_id = c.id "
        "GROUP BY c.id ORDER BY c.sort_order"
    ).fetchall()

    memories = []
    active_category = None
    if category_id:
        memories = db.execute(
            "SELECT * FROM memories WHERE category_id = ? ORDER BY memory_date DESC",
            (category_id,),
        ).fetchall()
        active_category = db.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()

    db.close()
    return render_template(
        "albums.html",
        categories=categories,
        memories=memories,
        active_category=active_category,
    )


@app.route("/letters")
@login_required
def letters():
    db = get_db()
    all_letters = db.execute(
        "SELECT * FROM letters ORDER BY created_at DESC"
    ).fetchall()
    db.close()
    return render_template(
        "letters.html",
        letters=all_letters,
        partner1=config.PARTNER_1,
        partner2=config.PARTNER_2,
    )


@app.route("/letters/new", methods=["POST"])
@login_required
def new_letter():
    author = request.form.get("author", "").strip()
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    if not all([author, title, content]):
        flash("Please fill in all fields.")
        return redirect(url_for("letters"))

    db = get_db()
    db.execute(
        "INSERT INTO letters (author, title, content) VALUES (?, ?, ?)",
        (author, title, content),
    )
    db.commit()
    db.close()
    flash("Letter sent with love! 💌")
    return redirect(url_for("letters"))


@app.route("/letters/<int:letter_id>/delete", methods=["POST"])
@login_required
def delete_letter(letter_id):
    db = get_db()
    db.execute("DELETE FROM letters WHERE id = ?", (letter_id,))
    db.commit()
    db.close()
    flash("Letter deleted.")
    return redirect(url_for("letters"))


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    db = get_db()
    categories = db.execute(
        "SELECT * FROM categories ORDER BY sort_order"
    ).fetchall()

    if request.method == "POST":
        files = request.files.getlist("files")
        title = request.form.get("title", "").strip()
        caption = request.form.get("caption", "").strip()
        category_id = request.form.get("category_id") or None
        memory_date = request.form.get("memory_date") or None
        uploaded_by = request.form.get("uploaded_by", "").strip()

        if not files or not files[0].filename:
            flash("Please select at least one file.")
            return redirect(url_for("upload"))

        saved = 0
        for f in files:
            ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
            if ext in config.ALLOWED_IMAGE_EXTENSIONS:
                media_type = "image"
            elif ext in config.ALLOWED_VIDEO_EXTENSIONS:
                media_type = "video"
            else:
                continue

            unique_name = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(config.UPLOAD_FOLDER, unique_name)
            f.save(filepath)

            # Generate thumbnail for images
            thumbnail = None
            if media_type == "image":
                thumbnail = _make_thumbnail(filepath, unique_name)

            file_title = title if title else f.filename.rsplit(".", 1)[0]
            db.execute(
                "INSERT INTO memories (title, caption, filename, thumbnail, media_type, "
                "category_id, memory_date, uploaded_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (file_title, caption, unique_name, thumbnail, media_type,
                 category_id, memory_date, uploaded_by),
            )
            saved += 1

        db.commit()
        db.close()
        flash(f"{saved} memory(ies) uploaded! 🎉")
        return redirect(url_for("timeline"))

    db.close()
    return render_template(
        "upload.html",
        categories=categories,
        partner1=config.PARTNER_1,
        partner2=config.PARTNER_2,
    )


@app.route("/memory/<int:memory_id>/delete", methods=["POST"])
@login_required
def delete_memory(memory_id):
    db = get_db()
    memory = db.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
    if memory:
        # Delete files
        filepath = os.path.join(config.UPLOAD_FOLDER, memory["filename"])
        if os.path.exists(filepath):
            os.remove(filepath)
        if memory["thumbnail"]:
            thumb_path = os.path.join(config.UPLOAD_FOLDER, "thumbnails", memory["thumbnail"])
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
        db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        db.commit()
    db.close()
    flash("Memory deleted.")
    return redirect(request.referrer or url_for("timeline"))


# ------------------------------------------------------------------
# API endpoints for AJAX
# ------------------------------------------------------------------

@app.route("/api/categories", methods=["POST"])
@login_required
def api_add_category():
    data = request.get_json()
    name = data.get("name", "").strip()
    emoji = data.get("emoji", "💕").strip()
    if not name:
        return jsonify({"error": "Name required"}), 400

    db = get_db()
    try:
        db.execute(
            "INSERT INTO categories (name, emoji) VALUES (?, ?)", (name, emoji)
        )
        db.commit()
        cat_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.close()
        return jsonify({"id": cat_id, "name": name, "emoji": emoji})
    except Exception:
        db.close()
        return jsonify({"error": "Category already exists"}), 409


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_thumbnail(filepath, filename):
    try:
        from PIL import Image
        img = Image.open(filepath)
        img.thumbnail((400, 400))
        thumb_name = f"thumb_{filename}"
        thumb_dir = os.path.join(config.UPLOAD_FOLDER, "thumbnails")
        # Convert RGBA to RGB for JPEG compatibility
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        thumb_path = os.path.join(thumb_dir, thumb_name.rsplit(".", 1)[0] + ".jpg")
        img.save(thumb_path, "JPEG", quality=80)
        return thumb_name.rsplit(".", 1)[0] + ".jpg"
    except Exception:
        return None


@app.template_filter("datefmt")
def datefmt(value):
    if not value:
        return ""
    try:
        d = datetime.strptime(str(value), "%Y-%m-%d")
        return d.strftime("%B %d, %Y")
    except ValueError:
        return value


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
