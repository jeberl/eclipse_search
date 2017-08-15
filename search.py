# -*- coding: utf-8 -*-
import os
import io
import cPickle as pickle
import shelve
import requests
from pidfile import PIDFile
from werkzeug.contrib.fixers import ProxyFix
from flask import Flask, render_template, send_from_directory, jsonify


app = Flask(__name__, static_url_path='')
app.wsgi_app = ProxyFix(app.wsgi_app)

USERS_DUMMY_DICT = shelve.open('./storage/user.dict')

SOLR_URL = os.environ.get('DB_URL')
SOLR_CORE_NAME = os.environ.get('SOLR_CORE')
SOLR_QUERY_PARAMS = "&".join(
    ["", "hl.fl=Response,Question", "hl.simple.pre=%3Chl%3E", "hl.simple.post=%3C/hl%3E", "hl.fragsize=0", "hl=on",
     "indent=on", "wt=json"])
SAVED_DATA_LOCATION = 'data/csv_data.csv'

PORT = os.environ.get('ECLIPSE_PORT', 5105)

SCHEME = 'https' if os.environ.get('URL_SCHEME', None) else 'http'


def build_url(query, with_params):
    if with_params:
        return "/".join([SOLR_URL, SOLR_CORE_NAME, "select?q=" + query, SOLR_QUERY_PARAMS])
    return "/".join([SOLR_URL, SOLR_CORE_NAME, query])


@app.route('/css/<filename>')
def serve_css_static(filename):
    return send_from_directory(os.path.join('.', 'css'), filename)


@app.route('/css/images/<filename>')
def serve_images_static(filename):
    return send_from_directory(os.path.join('.', 'css', 'images'), filename)

@app.route('/js/<filename>')
def serve_js_static(filename):
    return send_from_directory(os.path.join('.', 'js'), filename)


@app.route('/query/<path:query>', methods=['POST'])
def solr_query(query):
    resp = requests.get(build_url(query, True))
    if resp.status_code == 400:
        return jsonify({"num_found": 'ERR', "html": "<h3>&emsp;Error in Query</h3>"})
    if resp:
        json = resp.json()
        html = ''
        for doc in json['response']['docs']:
            highlights = json.get("highlighting", {}).get(doc["id"], {})
            highlights = {key: value[0] for key, value in highlights.items()}
            doc.update(highlights)
            html += render_template('solr_item.html', data=doc)
        if html:
            return jsonify({"num_found": json['response']['numFound'], "html": html})
    return jsonify({"num_found": 0, "html": ""})


@app.route('/delete/<int:id_to_delete>', methods=['POST'])
def delete(id_to_delete):
    try:
        deletions = pickle.load(open("./storage/deletions.pickle", "rb"))
    except (EOFError, IOError):
        deletions = {}
    deletions[id_to_delete] = True
    pickle.dump(deletions, open("./storage/deletions.pickle", "wb"))
    return solr_delete(id_to_delete=id_to_delete)

def solr_delete(id_to_delete=None):
    query = 'id:' + str(id_to_delete) if id_to_delete else '*:*'
    resp = requests.get(
        build_url("update?stream.body=<delete><query>{}</query></delete>&commit=true&wt=json".format(query), False))
    return jsonify(resp.json()['responseHeader']['status']) if resp else None

@app.route('/comment/solr/<path:query>', methods=['POST'])
def comment(query):
    path = query.split("/")
    _id = str(path[0])
    comment = str("".join(path[1:]))
    try:
        comments = pickle.load(open("./storage/comments.pickle", "rb"))
    except (EOFError, IOError):
        comments = {}
    comments[_id] = comment
    pickle.dump(comments, open("./storage/comments.pickle", "wb"))
    return solr_comment(_id, comment)


def solr_comment(_id, comment):
    headers = {'Content-type': 'application/json'}
    data = {"add": {"doc": {"id": _id, 'comments': {"set": comment}}}}
    resp = requests.get(build_url('update?commit=true', None), headers=headers, data=str(data))
    if resp:
        return jsonify(resp.json()['responseHeader']['status'])
    return None

@app.route('/reindex', methods=['POST'])
def solr_reindex():
    print "Reindexing files to solr:"
    solr_delete()
    print "     deleted all files"

    resp = solr_add_csv()
    print "     added csv files"

    try:
        comments = pickle.load(open("./storage/comments.pickle", "rb"))
        for _id, comment in comments.iteritems():
            solr_comment(_id, comment)
            print "     commented on id # {}".format(_id)
    except (EOFError, IOError):
        pass

    try:
        deletions = pickle.load(open("./storage/deletions.pickle", "rb"))
        for _id, _ in deletions.iteritems():
            solr_delete(_id)
            print "     deleted response id # {}".format(_id)
    except (EOFError, IOError):
        pass
    return jsonify(resp.json()['responseHeader']['status'])

def solr_add_csv():
    with io.open(SAVED_DATA_LOCATION, 'r', encoding='utf-8-sig') as csvfile:
        data = csvfile.read()
        data.rstrip()
        return requests.get(build_url("update?commit=true&wt=json", None), data=data.encode('utf-8'),
                            headers={"Content-type":"application/csv"})

@app.route('/search')
def search():
    companies_query = build_url("select/?q=*%3A*&rows=0&facet=on&facet.field=Company&wt=json", False)
    companies = requests.get(companies_query).json()['facet_counts']['facet_fields']['Company']
    company_names = [str(name) for name in companies if isinstance(name, unicode)]
    return render_template('solr.html', data={'companies': company_names, 'num_results': 0})

@app.route('/')
def index():
    return render_template('solr.html', data={})


if __name__ == '__main__':
    with PIDFile("./storage/eclipse_search.pid"):
        app.run(port=PORT, host='0.0.0.0')
