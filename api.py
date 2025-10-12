from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api, reqparse, abort, fields, marshal_with
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
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    status = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"User(name = {self.username}', email = '{self.email}'. status = '{self.status}')"
    
user_arguments = reqparse.RequestParser()
user_arguments.add_argument("username", type=str, help="Username is required", required=True)
user_arguments.add_argument("email", type=str, help="Email is required", required=True)
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
    @marshal_with(userFields)
    def post(self):
        args = user_arguments.parse_args()
        print(f"Creating user with args: {args}")
        
        # Check if user already exists
        existing_user = UserModel.query.filter_by(username=args['username']).first()
        if existing_user and existing_user.status:
            print(f"Username {args['username']} already exists")
            abort(400, message=f"Username {args['username']} already exists")
            
        existing_email = UserModel.query.filter_by(email=args['email']).first()
        if existing_email and existing_email.status:
            print(f"Email {args['email']} already exists")
            abort(400, message=f"Email {args['email']} already exists")
        
        try:
            user = UserModel(username=args['username'], email=args['email'])
            user.status = True
            db.session.add(user)
            db.session.commit()
            
            users = UserModel.query.filter_by(status=True).all()
            print(f"Successfully created user, returning {len(users)} users")
            return users, 201
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            db.session.rollback()
            abort(500, message=f"Internal server error: {str(e)}")
    
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