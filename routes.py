###############################
####### SETUP (OVERALL) #######
###############################

# Import statements
import os
from flask import Flask, render_template, session, redirect, url_for, flash, request
from flask_script import Manager
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import Required, Length, ValidationError
from flask_sqlalchemy import SQLAlchemy
import requests
import json

# App setup code
app = Flask(__name__)
app.debug = True

# All app.config values
app.config['SECRET_KEY'] = 'hard to guess string'
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://localhost/becclestmidterm"
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Other setup
manager = Manager(app)  # In order to use manager
db = SQLAlchemy(app)  # For database use
nyt_key = '70d3f98def8249ee834158a13ff09cda'

#############################
######## HELPER FXNS ########
#############################


def get_or_create_author(name):
    author = Author.query.filter_by(name=name).first()
    if not author:
        author = Author(name=name)
        db.session.add(author)
        db.session.commit()
    return author


def get_or_create_title(title):
    book = Book.query.filter_by(title=title).first()
    if not book:
        book = Book(title=title)
        db.session.add(book)
        db.session.commit()
    return book


def get_books_result(author):
    baseurl = 'https://api.nytimes.com/svc/books/v3/lists/best-sellers/history'
    params = {'api-key': nyt_key}
    params['author'] = author
    response = requests.get(baseurl, params=params)
    results = json.loads(response.text)
    return (results)

##################
##### MODELS #####
##################


class Name(db.Model):
    __tablename__ = "names"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))

    def __repr__(self):
        return "{} (ID: {})".format(self.name, self.id)


class Author(db.Model):
    __tablename__ = "authors"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    books = db.relationship('Book', backref='Author')

    def __repr__(self):
        return (self.name)


class Book(db.Model):
    __tablename__ = "books"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    desc = db.Column(db.String(255))
    review = db.Column(db.String(255))
    price = db.Column(db.Integer)
    author_id = db.Column(db.Integer, db.ForeignKey("authors.id"))

    def __repr__(self):
        return "{}:  {} | ${}".format(self.title, self.desc, self.price)


###################
###### FORMS ######
###################

def check_authorname(self, field):
    if len(field.data.split()) < 2:
        raise ValidationError('The Author Name MUST be first and last!')


class AuthorForm(FlaskForm):
    author = StringField("Enter the author's name.", validators=[
        Required(), Length(1, 64), check_authorname])
    submit = SubmitField()


class NameForm(FlaskForm):
    name = StringField("Please enter your name.", validators=[Required()])
    submit = SubmitField()

####################
#####   Routes   ###
####################

# Error handling routes -


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@app.route('/', methods=["GET", "POST"])  # change
def home():
    form = AuthorForm()
    if form.validate_on_submit():
        authorname = form.author.data
        author = get_or_create_author(name=authorname)
        db.session.add(author)
        db.session.commit()
        return redirect(url_for('see_books'))
    return render_template('home.html', form=form)

@app.route('/names',methods=["GET","POST"])
def names():
    form = NameForm()
    if form.validate_on_submit():
        name = form.name.data
        full_name = Name(name=name)
        db.session.add(full_name)
        db.session.commit()
        return redirect(url_for('all_names'))
    return render_template('base.html',form=form)


@app.route('/all_names')
def all_names():
    names = Name.query.all()
    return render_template('name_example.html', names=names)


@app.route('/books', methods=["GET", "POST"])  # change
def see_books():
    bestselling_books = []
    authors = Author.query.all()
    auth = authors[-1]
    stories = get_books_result(auth)
    info = stories['results']
    if len(info) > 0 and "description" in info[0]:
        for bks in info:
            cmd = bks['title']
            ath = bks['author']
            desc = bks['description']
            price = bks['price']
            reviews = bks['reviews'][0]['book_review_link']
            book1 = Book(title=cmd, author_id=auth.id,
                         desc=desc, price=price, review=reviews)
            db.session.add(book1)
            db.session.commit()
            book2 = [cmd, ath, desc, price, reviews]
            bestselling_books.append(book2)
        else:
            print ('Error!')
    return render_template('auth_books.html', book=book2, bestselling_books=bestselling_books)


@app.route('/authors')
def see_all_authors():
    all_authors = []
    authors = Author.query.all()
    for a in authors:
        user = Author.query.filter_by(id=a.id).first()
        all_authors.append(
            (user.name, len(Book.query.filter_by(author_id=a.id).all())))
    return render_template('all_authors.html', usernames=all_authors)


@app.route('/all_books')
def see_all_books():
    all_books = []
    books = Book.query.all()
    for b in books:
        author = Author.query.filter_by(id=b.author_id).first()
        all_books.append((b.title, author.name))
    return render_template('books.html', bestselling_books=all_books)


if __name__ == '__main__':
    db.create_all()
    manager.run()
    app.run(use_reloader=True)
