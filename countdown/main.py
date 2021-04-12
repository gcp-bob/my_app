# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from flask import flash, Flask, Markup, redirect, render_template
from flask import request
from flask import url_for
from google.cloud import error_reporting
import logging
import google.cloud.logging
import firestore
from datetime import *
import datetime

app = Flask(__name__)
app.config.update(
    SECRET_KEY='secret'
)

app.debug = False
app.testing = False

# Configure Google Stackdriver logging
if not app.testing:
    logging.basicConfig(level=logging.INFO)
    client = google.cloud.logging.Client()
    # Attaches a Google logging handler to the root logger
    client.setup_logging()


# Display a list of entries
@app.route('/')
def display():
    start_after = request.args.get('start_after', None)
    people, last_firstname = firestore.next_page(start_after=start_after)
    return render_template('list.html', people=people, last_firstname=last_firstname)


# Display the details and options for one entry
@app.route('/people/<entry_id>')
def view(entry_id):
    entry = firestore.read(entry_id)
    return render_template('view.html', entry=entry)


# Add a new entry
@app.route('/people/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        data = request.form.to_dict(flat=True)
        entry = firestore.create(data)
        return redirect(url_for('.view', entry_id=entry['id']))
    return render_template('form.html', action='Add', entry={})


# Edit the details of one entry
@app.route('/people/<entry_id>/edit', methods=['GET', 'POST'])
def edit(entry_id):
    entry = firestore.read(entry_id)
    if request.method == 'POST':
        data = request.form.to_dict(flat=True)
        entry = firestore.update(data, entry_id)
        return redirect(url_for('.view', entry_id=entry['id']))
    return render_template('form.html', action='Edit', entry=entry)


# Delete an existing entry
@app.route('/people/<entry_id>/delete')
def delete(entry_id):
    firestore.delete(entry_id)
    return redirect(url_for('.display'))


# Displays details and action button for birthday countdown
@app.route('/people/<entry_id>/birthday')
def birthday(entry_id):
    entry = firestore.read(entry_id)
    return render_template('countdown.html', entry=entry)


# Code for the birthday countdown
@app.route('/people/<entry_id>/birthday/calculate', methods=['POST'])
def countdown(entry_id):
    entry = firestore.read(entry_id)
    yob_id = request.form.get('yob', type=int)
    mob_id = request.form.get('mob', type=int)
    dob_id = request.form.get('dob', type=int)
    # Get Today's Date
    today = date.today()
    today_txt = "Today: " + today.strftime('%A %d, %b %Y')
    isvalid = True
    try:
        datetime.datetime(yob_id, mob_id, dob_id)
    except ValueError:
        isvalid = False
    if isvalid:
        dob = date(yob_id, mob_id, dob_id)
    else:
        prb_dob = "Please edit your birth date in Firestore to a valid one, different than 30th of February ;)"
        return render_template('countdown.html', entry=entry, prb_dob=prb_dob)
    if date(yob_id, mob_id, dob_id) >= today:
        prb_dob = "Please edit your birth date in Firestore to a valid one, before today :)"
        return render_template('countdown.html', entry=entry, prb_dob=prb_dob)
    # Calculate number of days lived
    number_of_days = (today - dob).days
    # Convert this into whole years to display the age
    age = number_of_days // 365
    age_txt = "You are " + str(age) + " years old."
    # Retrieve the day of the week (Monday to Sunday) corresponding to the birth date
    day = dob.strftime("%A")
    dob_txt = "You were born on a " + day + "."
    doe_txt = "You have spent " + str(number_of_days) + " days on Earth."
    # Calculating the number of days until next birthday
    this_year = today.year
    next_birthday = date(this_year, mob_id, dob_id)
    if today < next_birthday:
        gap = (next_birthday - today).days
        count_down = "Your birthday is in " + str(gap) + " days."
    elif today == next_birthday:
        count_down = "Today is your birthday! Happy Birthday!"
    else:
        next_birthday = date(this_year + 1, mob_id, dob_id)
        gap = (next_birthday - today).days
        count_down = "Your birthday is in " + str(gap) + " days."
    return render_template('countdown.html', entry=entry, today_txt=today_txt,
                           age_txt=age_txt, dob_txt=dob_txt, doe_txt=doe_txt, count_down=count_down)


# Generate a custom log entry accessible in Cloud Console
@app.route('/logs')
def logs():
    logging.info('Hey, you triggered a custom log entry. Good job!')
    flash(Markup('''You triggered a custom log entry. You can view it in the
        <a href="https://console.cloud.google.com/logs">Cloud Console</a>'''))
    return redirect(url_for('.display'))


# Generate an intentional exception
@app.route('/errors')
def errors():
    raise Exception('This is an intentional exception.')


# Add an error handler that reports exceptions to Stackdriver Error
# Reporting. Note that this error handler is only used when debug
# is False
@app.errorhandler(500)
def server_error(e):
    client = error_reporting.Client()
    client.report_exception(
        http_context=error_reporting.build_flask_context(request))
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


# This is only used when running locally. When running live, gunicorn runs
# the application.
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
