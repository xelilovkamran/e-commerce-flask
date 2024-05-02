from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
import base64
import os


env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
db = SQLAlchemy(app)


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    approved = db.Column(db.Boolean, default=False)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class UserProblem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('problems', lazy=True))
    company_id = db.Column(
        db.Integer, db.ForeignKey('company.id'), nullable=True)
    company = db.relationship(
        'Company', backref=db.backref('problems', lazy=True))


class ProblemReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    user_problem_id = db.Column(db.Integer, db.ForeignKey(
        'user_problem.id'), nullable=False)
    user_problem = db.relationship(
        'UserProblem', backref=db.backref('reviews', lazy=True))


def check_problems():
    problems = UserProblem.query.all()
    for problem in problems:
        if problem.company is None:
            db.session.delete(problem)
    db.session.commit()


def encode_string(string_to_encode):
    encoded_string = base64.b64encode(string_to_encode.encode()).decode()
    return encoded_string


def decode_string(base64_string):
    decoded_string = base64.b64decode(base64_string).decode()
    return decoded_string


@app.route('/', methods=['GET'])
def home():
    return jsonify({'status': 'running'})


@app.route('/company/awaiting', methods=['GET'])
def awaiting_companies():
    companies = Company.query.filter_by(approved=False).all()
    return jsonify([{"name": company.company_name} for company in companies])


@app.route('/company/approve/<int:id>', methods=['POST'])
def approve_company(id):
    company = Company.query.get(id)
    if company is not None:
        company.approved = True
        db.session.commit()
        return jsonify({'status': 'approved'})
    else:
        return jsonify({'status': 'company not found'})


@app.route('/company/reject/<int:id>', methods=['POST'])
def reject_company(id):
    company = Company.query.get(id)
    if company is not None:
        db.session.delete(company)
        db.session.commit()
        check_problems()
        return jsonify({'status': 'rejected'})
    else:
        return jsonify({'status': 'company not found'})


@app.route("/create/admin", methods=["POST"])
def create_admin():
    username = request.json.get("username")
    password = request.json.get("password")
    admin = Admin(username=username, password=password)
    db.session.add(admin)
    db.session.commit()
    return jsonify({"status": "created"})


@app.route("/admin/all", methods=["GET"])
def get_admins():
    admins = Admin.query.all()
    return jsonify([{"username": admin.username} for admin in admins])


@app.route('/company/register', methods=['POST'])
def register_company():
    company_name = request.json.get('name')
    password = request.json.get('password')
    password = encode_string(password)
    company = Company(company_name=company_name, password=password)
    db.session.add(company)
    db.session.commit()
    return jsonify({'status': 'registered'})


@app.route('/user/register', methods=['POST'])
def register_user():
    user_name = request.json.get('name')
    password = request.json.get('password')
    password = encode_string(password)
    if user_name is not None and password is not None:
        user = User(username=user_name, password=password)
        db.session.add(user)
        db.session.commit()
        return jsonify({'status': 'registered'})
    else:
        return jsonify({'status': 'company not found'})


@app.route('/company/login', methods=['POST'])
def login_company():
    company_name = request.json.get('name')
    password = request.json.get('password')
    password = encode_string(password)
    company = Company.query.filter_by(
        company_name=company_name, password=password).first()
    if company is not None:
        return jsonify({'status': 'success', "session_id": encode_string(company_name)})
    else:
        return jsonify({'status': 'failed'})


@app.route('/user/login', methods=['POST'])
def login_user():
    user_name = request.json.get('name')
    password = request.json.get('password')
    password = encode_string(password)
    user = User.query.filter_by(username=user_name, password=password).first()
    if user is not None:
        return jsonify({'status': 'success', "session_id": encode_string(user_name)})
    else:
        return jsonify({'status': 'failed'})


@app.route('/user/add_problem', methods=['POST'])
def add_problem():
    user_name = request.json.get('user')
    problem = request.json.get('problem')
    company_name = request.json.get('company_name')
    user = User.query.filter_by(username=user_name).first()
    company = Company.query.filter_by(company_name=company_name).first()
    if user is not None:
        user_problem = UserProblem(
            description=problem, user=user, company=company)
        db.session.add(user_problem)
        db.session.commit()
        return jsonify({'status': 'added'})
    else:
        return jsonify({'status': 'user not found'})


@app.route('/user/<int:id>/problems', methods=['GET'])
def get_problems(id):
    # user = User.query.get(id=id)
    problems = UserProblem.query.filter_by(user_id=id).all()
    if problems is not None:
        result = []
        for problem in problems:
            reviews = []
            for review in problem.reviews:
                reviews.append(review.description)
            result.append(
                {'description': problem.description, 'reviews': review.description, 'company': problem.company.company_name})
        print(result)
        return jsonify(result)
    else:
        return jsonify({'status': 'user not found'})


@app.route("/admin/problems", methods=["GET"])
def get_all_problems():
    problems = UserProblem.query.all()
    result = []
    for problem in problems:
        reviews = []
        for review in problem.reviews:
            reviews.append(review.description)
        result.append(
            {'description': problem.description, 'reviews': reviews, 'user': problem.user.username, 'company': problem.company.company_name})
    return jsonify(result)


@app.route('/admin/review_problem/<int:id>', methods=['POST'])
def review_problem(id):
    problem = UserProblem.query.get(id)
    if problem is not None:
        description = request.json.get('description')
        review = ProblemReview(description=description, user_problem=problem)
        db.session.add(review)
        db.session.commit()
        return jsonify({'status': 'reviewed'})
    else:
        return jsonify({'status': 'problem not found'})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "localhost")
    app.run(debug=True, host=host, port=port)
