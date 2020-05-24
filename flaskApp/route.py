import os
import secrets
from PIL import Image
from flask import render_template, flash, redirect, url_for, request, abort
from flaskApp import app, bcrypt , db
from flaskApp.form import RegistrationForm, LoginForm, UpdateAccountForm, PostGrievanceForm
from flaskApp.models import User, Grievance
from flask_login import login_user, current_user, logout_user, login_required

@app.route("/")
@app.route("/home")
def home():
    page = request.args.get('page', 1, type=int)
    grievances = Grievance.query.order_by(Grievance.date_posted.desc()).paginate(page=page, per_page=3)
    return render_template('home.html', grievances=grievances)

@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # db.create_all()
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful! Please check Username and Password.', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    f_name, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pic', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    
    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data) 
            current_user.image_file = picture_file 
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your accout has been Updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pic/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form)


def save_grievance_picture(form_picture):
    random_hex = secrets.token_hex(8)
    f_name, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/grievance_pic', picture_fn)
    form_picture.save(picture_path)
    
    return picture_fn


@app.route("/grievance/new", methods=['GET', 'POST'])
@login_required
def new_grievance():
    form = PostGrievanceForm()
    if form.validate_on_submit():
        if form.grievance_picture.data:
            grievance_picture_file = save_grievance_picture(form.grievance_picture.data) 
            current_user.grievance_image_file = grievance_picture_file
        grievance = Grievance(category_grievance=form.category_grievance.data, title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(grievance)
        db.session.commit()
        flash('Your Grievance has been Sumbitted', 'success')
        grievance_image_file = url_for('static', filename='grievance_pic/' + current_user.grievance_image_file)
        return redirect(url_for('home'))
    return render_template('create_grievance.html', title='New Grievance', legend='New Grievance', form=form)


@app.route("/grievance/<int:grievance_id>")
def grievance(grievance_id):
    grievance = Grievance.query.get_or_404(grievance_id)
    return render_template('grievance.html', title=grievance.title, grievance=grievance)


@app.route("/grievance/<int:grievance_id>/update", methods=['GET', 'POST'])
def grievance_update(grievance_id):
    grievance = Grievance.query.get_or_404(grievance_id)
    if grievance.author != current_user:
        abort(403)
    form = PostGrievanceForm()
    if form.validate_on_submit():
        if form.grievance_picture.data:
            grievance_picture_file = save_grievance_picture(form.grievance_picture.data) 
            current_user.grievance_image_file = grievance_picture_file
        grievance.category_grievance = form.category_grievance.data
        grievance.title = form.title.data
        grievance.content = form.content.data
        db.session.commit()
        flash('Your Grievance has been updated!', 'success')
        grievance_image_file = url_for('static', filename='grievance_pic/' + current_user.grievance_image_file)
        return redirect(url_for('grievance', grievance_id=grievance.id))
    elif request.method == 'GET':
        form.category_grievance.data = grievance.category_grievance
        form.title.data = grievance.title
        form.content.data = grievance.content
    return render_template('create_grievance.html', title='Update Grievance', legend='Update Grievance', form=form)



@app.route("/grievance/<int:grievance_id>/delete", methods=['POST'])
def grievance_delete(grievance_id):
    grievance = Grievance.query.get_or_404(grievance_id)
    if grievance.author != current_user:
        abort(403)
    db.session.delete(grievance)
    db.session.commit()
    flash('Your Grievance has been deleted!', 'success')
    return redirect(url_for('home'))


@app.route("/user/<string:username>")
def user_grievances(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    grievances = Grievance.query.filter_by(author=user)\
        .order_by(Grievance.date_posted.desc())\
        .paginate(page=page, per_page=3)
    return render_template('user_grievances.html', grievances=grievances, user=user)