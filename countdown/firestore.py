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

import firebase_admin
from firebase_admin import firestore
from google.cloud import firestore
# from firebase_admin import credentials

# Use a service account
# cred = credentials.Certificate("/path/to/service_account_key.json")
# In our case, we define the env variable to allow authentication by running the following command:
# export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service_account_key.json
firebase_admin.initialize_app()


def document_to_dict(doc):
    if not doc.exists:
        return None
    doc_dict = doc.to_dict()
    doc_dict['id'] = doc.id
    return doc_dict


def next_page(limit=10, start_after=None):
    db = firestore.Client()

    query = db.collection(u'Entry').limit(limit).order_by(u'firstname')

    if start_after:
        # Construct a new query starting at this document.
        query = query.start_after({u'firstname': start_after})

    docs = query.stream()
    docs = list(map(document_to_dict, docs))

    last_firstname = None
    if limit == len(docs):
        # Get the last document from the results and set as the last title.
        last_firstname = docs[-1][u'firstname']
    return docs, last_firstname


def read(entry_id):
    db = firestore.Client()
    entry_ref = db.collection(u'Entry').document(entry_id)
    snapshot = entry_ref.get()
    return document_to_dict(snapshot)


def update(data, entry_id=None):
    db = firestore.Client()
    entry_ref = db.collection(u'Entry').document(entry_id)
    entry_ref.set(data)
    return document_to_dict(entry_ref.get())


create = update


def delete(id):
    db = firestore.Client()
    entry_ref = db.collection(u'Entry').document(id)
    entry_ref.delete()
