from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "car"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'static/photos/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif', 'mp4'])  # Add 'mp4' for video

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    likes = db.relationship('Like', backref='user', lazy=True)

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    likes = db.relationship('Like', backref='photo', lazy=True)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    photo_id = db.Column(db.Integer, db.ForeignKey('photo.id'), nullable=False)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def upload_form():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        photos = Photo.query.all()
        return render_template('upload.html', user=user, photos=photos)
    else:
        return redirect(url_for('login'))

@app.route('/', methods=['POST'])
def upload_image():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)

        if 'files[]' not in request.files:
            flash('No file part')
            return redirect(request.url)

        files = request.files.getlist('files[]')

        # Use a session variable to store the uploaded filenames
        file_names = session.get('file_names', [])

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_names.append(filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                # Save photo details to the database
                photo = Photo(filename=filename)
                db.session.add(photo)
                db.session.commit()

            else:
                return redirect(request.url)

        # Update the session variable
        session['file_names'] = file_names

        return redirect(url_for('upload_form'))

    else:
        return redirect(url_for('login'))

@app.route('/display/<filename>')
def display_image(filename):
    return redirect(url_for('static', filename='photos/' + filename), code=301)

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session['user_id'] = user.id
            return redirect(url_for('upload_form'))

    return render_template('login.html')

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash('')
        else:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()

    return render_template('register.html')

@app.route('/like/<int:photo_id>', methods=['GET', 'POST'])
def like(photo_id):
    if 'user_id' in session:
        user_id = session['user_id']
        like = Like.query.filter_by(user_id=user_id, photo_id=photo_id).first()

        if not like:
            like =Like(user_id=user_id, photo_id=photo_id)
            db.session.add(like)

            # Increment the like count for the associated photo
            photo = Photo.query.get(photo_id)
            photo.likes.append(like)

            db.session.commit()

        return redirect(url_for('upload_form'))
    else:
        return redirect(url_for('login'))
@app.route('/dislike/<int:photo_id>', methods=['POST'])
def dislike(photo_id):
    if 'user_id' in session:
        user_id = session['user_id']

        # Get the like associated with the user and photo
        like = Like.query.filter_by(user_id=user_id, photo_id=photo_id).first()

        if like:
            # Remove the like from the photo's likes
            photo = Photo.query.get(photo_id)
            if like in photo.likes:
                photo.likes.remove(like)

            # Delete the like from the database
            db.session.delete(like)
            db.session.commit()

        return redirect(url_for('upload_form'))
    else:
        return redirect(url_for('login'))


@app.route('/delete/<int:photo_id>', methods=['POST'])
def delete_photo(photo_id):
    if 'user_id' in session:
        user_id = session['user_id']

        # Check if the user has the right to delete the photo
        photo = Photo.query.get(photo_id)

        if not photo:

            return redirect(url_for('upload_form'))

        # Ensure that the user deleting the photo is the one who uploaded it
        if photo.user.id == user_id:
            # Remove the photo or video from the file system
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], photo.filename)
            os.remove(file_path)

            # Remove the photo or video from the database
            db.session.delete(photo)
            db.session.commit()


        return redirect(url_for('upload_form'))

    else:
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('upload_form'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        app.run(debug=True,host="0.0.0.0")
