from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class FlashcardForm(FlaskForm):
    front_content = StringField('Front Content', validators=[DataRequired()])
    back_content = StringField('Back Content', validators=[DataRequired()])
    submit = SubmitField('Submit')