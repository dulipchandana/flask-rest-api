from flask import Flask, send_from_directory, request
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api, reqparse, abort, fields, marshal_with, marshal
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
api = Api(app)

# Initialize database tables
def init_db():
    with app.app_context():
        db.create_all()

class UserModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    status = db.Column(db.Boolean, nullable=False, default=True)
    
    __table_args__ = (
        db.Index('ix_user_model_username_status', 'username', 'status', unique=True),
        db.Index('ix_user_model_email_status', 'email', 'status', unique=True),
    )

    def __repr__(self):
        return f"User(name = {self.username}', email = '{self.email}'. status = '{self.status}')"
    
def validate_length(value, field_name, max_length):
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    if len(value) > max_length:
        raise ValueError(f"String length exceeds maximum allowed length of {max_length} for {field_name}")
    return value

def validate_username(username):
    if not username:
        raise ValueError("Username is required")
    return validate_length(username, "username", 80)

def validate_email(email):
    if not email:
        raise ValueError("Email is required")
    return validate_length(email, "email", 120)

user_arguments = reqparse.RequestParser()
user_arguments.add_argument("username", type=validate_username, help="Username is required and must not exceed 80 characters", required=True)
user_arguments.add_argument("email", type=validate_email, help="Email is required and must not exceed 120 characters", required=True)
userFields = {
    'id': fields.Integer,
    'username': fields.String,
    'email': fields.String,
    'status': fields.Boolean
}

class Users(Resource):
    @marshal_with(userFields)
    def get(self):
        users = UserModel.query.filter_by(status=True).all()
        return users, 200
    def post(self):
        try:
            if not request.is_json:
                return {'message': 'Invalid JSON payload'}, 400

            try:
                json_data = request.get_json()
            except Exception:
                return {'message': 'Invalid JSON payload'}, 400
                
            if not json_data:
                return {'message': 'Invalid JSON payload'}, 400

            errors = {}
            if 'username' not in json_data:
                errors['username'] = "Username is required"
            if 'email' not in json_data:
                errors['email'] = "Email is required"
            
            if errors:
                return {'message': errors}, 400
            
            if len(json_data.get('username', '')) > 80:
                return {'message': 'String length exceeds maximum allowed length of 80 for username'}, 400
                
            if len(json_data.get('email', '')) > 120:
                return {'message': 'String length exceeds maximum allowed length of 120 for email'}, 400
            
            args = user_arguments.parse_args(strict=True)
            print(f"Creating user with args: {args}")
        except Exception as e:
            error_msg = str(e)
            if "required" in error_msg.lower():
                return {'message': 'Missing required field'}, 400
            return {'message': error_msg}, 400
            
        # Check if user already exists and is active
        existing_user = UserModel.query.filter_by(username=args['username'], status=True).first()
        if existing_user:
            print(f"Username {args['username']} already exists")
            return {'message': f"Username {args['username']} already exists"}, 400
            
        existing_email = UserModel.query.filter_by(email=args['email'], status=True).first()
        if existing_email:
            print(f"Email {args['email']} already exists")
            return {'message': f"Email {args['email']} already exists"}, 400
        
        try:
            user = UserModel(username=args['username'], email=args['email'])
            user.status = True
            db.session.add(user)
            db.session.commit()
            return marshal(user, userFields), 201
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            db.session.rollback()
            return {'message': f"Internal server error: {str(e)}"}, 500
    
class User(Resource):
    @marshal_with(userFields)
    def get(self, user_id):
        user = UserModel.query.filter_by(id=user_id,status=True).first()
        if not user:
            abort(404, message="Could not find user with that id")
        return user, 200
    @marshal_with(userFields)
    def put(self, user_id):
        args = user_arguments.parse_args()
        user = UserModel.query.filter_by(id=user_id,status=True).first()
        if not user:
            abort(404, message="Could not find user with that id")
        user.username = args['username']
        user.email = args['email']
        db.session.commit()
        return user, 200
    def delete(self, user_id):
        user = UserModel.query.filter_by(id=user_id).first()
        if not user:
            abort(404, message="Could not find user with that id")
        user.status = False
        db.session.commit()
        # Alternatively, to permanently delete the user, uncomment the following lines:
        db.session.commit()
        return '', 204
api.add_resource(Users, "/api/users")
api.add_resource(User, "/api/users/<int:user_id>")

# Swagger UI configuration
SWAGGER_URL = '/api/docs'
API_URL = '/static/swagger.yaml'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "User Management API"
    }
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

@app.route('/static/swagger.yaml')
def send_swagger_file():
    return send_from_directory('resource', 'swagger.yaml')

@app.route('/')
def home():
    return 'Hello, World!'

if __name__ == '__main__':
    init_db()  # Initialize database tables
    app.run(debug=True)