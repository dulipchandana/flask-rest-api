# create virtual envirnment 
py -m venv .venv
# activate the virtula envirnment 
source .venv/Scripts/activate

# deactivate the virtual envirnemt
deactivate

# add the flask dependansy 
pip install flask
pip install flask_restful
pip install flask_sqlalchemy

# create the requirements.txt
pip freeze > requirements.txt