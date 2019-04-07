"""
    GitHub Example
    --------------

    Shows how to authorize users with Github.

"""
from flask import Flask, request, g, session, redirect, url_for, render_template
from flask import render_template_string, jsonify
from flask_github import GitHub
import pymongo
import copy
import pprint
import requests
import json

import base64

from github import Github

SECRET_KEY = 'development key'
DEBUG = True

# Set these values
GITHUB_CLIENT_ID = 'Iv1.8791cf1242eb0cc5'
GITHUB_CLIENT_SECRET = '02cb36309afd5122f1779910a24505ee7e70e11c'

# setup flask
app = Flask(__name__)
app.config.from_object(__name__)

# setup github-flask
github = GitHub(app)
# print github

mongo = pymongo.MongoClient()['kidogit']
users = mongo.users

# https://kgit.ngrok.io/home?installation_id=791563&setup_action=install

class User:
    # id = 0
    # github_access_token = ''
    # github_id = 0
    # github_login = ''

    def __init__(self, data):
        data = data or {}
        for k, v in data.items():
            setattr(self, k, v)

    # def __init__(self, github_access_token):
    #     self.github_access_token = github_access_token
    def to_json(self, safe):
        if safe:
            res = copy.deepcopy(self.__dict__)
            res.pop('password', 0)
            return res
        return self.__dict__

    def save(self):
        res = users.insert_one(copy.deepcopy(self.__dict__))
        if not res.acknowledged:
            return jsonify(message='Error in saving user in database', statuscode=500), 500
        else:
            return jsonify(message='user Saved successfully.', statuscode=200), 200

    @staticmethod
    def get_one(args, ffilter):
        try:
            user = users.find_one(args, ffilter)
            if user:
                return User(user)
            return None
        except Exception as ex:
            print "[UserModel Error] Get user by email ", ex.args
        return None


@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.get_one(args={'github_id': session['user_id']}, ffilter={'_id': 0})


@app.after_request
def after_request(response):
    # db_session.remove()
    return response


@app.route('/')
def index():
    # session['user_id'] = None
    if g.user:
        # t = 'Hello! %s <a href="{{ url_for("user") }}">Get user</a><br> ' \
        #     '<a href="{{ url_for("repo") }}">Get repo</a><br>' \
        #     ' <a href="{{ url_for("pushFile") }}">Push a file</a> <br>' \
        #     '<a href="{{ url_for("logout") }}">Logout</a><br>'
        # t %= g.user.github_login
        return render_template('home.html', user=g.user.github_login)
    else:
        # t = 'Hello! <a href="{{ url_for("login") }}">Login</a>'
        return render_template('home.html', user={})
    # return render_template_string(t)


@app.route('/home')
def home():
    _user = User.get_one(args={'github_id': session.get('user_id')}, ffilter={'_id': 0})
    token = _user.github_access_token
    owner = _user.github_login

    # for repo in Github(_user.github_access_token).get_user().get_repos():
    #     print(repo.name)

    url = "https://api.github.com/repos/{owner}/{repo}/contents".format(owner=owner, repo='kidogit')

    res = requests.get(url, headers={"Authorization": "token " + token})
    pprint.pprint(res.json())

    if g.user:
        return render_template('home.html', user=g.user.github_login)
        # t = 'Hello! %s <a href="{{ url_for("user") }}">Get user</a> <br>' \
        #     '<a href="{{ url_for("repo") }}">Get repo</a> <br>' \
        #     ' <a href="{{ url_for("pushFile") }}">Push a file</a> <br>' \
        #     '<a href="{{ url_for("logout") }}">Logout</a><br>'
        # t %= g.user.github_login
    else:
        return render_template('home.html', user={})
        # t = 'Hello! <a href="{{ url_for("login") }}">Login</a>'
    # return render_template_string(t)


@github.access_token_getter
def token_getter():
    user = g.user
    if user is not None:
        return user.github_access_token


@app.route('/github-callback')
@github.authorized_handler
def authorized(access_token):
    next_url = request.args.get('next') or url_for('index')
    if access_token is None:
        return redirect(next_url)

    # user = User.query.filter_by(github_access_token=access_token).first()
    _user = User.get_one(args={'github_access_token': access_token}, ffilter={'_id': 0})
    if _user is None:
        g.user = _user
        # github_user = github.get('/user')
        github_user = Github(access_token).get_user()
        pprint.pprint(github_user)
        # _user.github_id = github_user.id
        # _user.github_login = github_user.login
        _user = User({
            'github_access_token': access_token,
            'github_id': github_user.id,
            'github_login': github_user.login
        })
        pprint.pprint(_user)
        User.save(_user)
        # _user.github_access_token = access_token

    # Not necessary to get these details here
    # but it helps humans to identify users easily.
    g.user = _user
    github_user = Github(access_token).get_user()
    _user.github_id = github_user.id
    _user.github_login = github_user.login

    # db_session.commit()

    session['user_id'] = _user.github_id
    return redirect(next_url)


@app.route('/webhook', methods=['POST'])
def appwebhook():
    print 'receiving a webhook...'
    pprint.pprint(request.json)
    # https://kgit.ngrok.io/home?installation_id=775876&setup_action=install
    return redirect(url_for('home'))


@app.route('/content_reference', methods=['POST', 'GET'])
def content_reference():
    print 'content_reference'
    return redirect(url_for('home'))


@app.route('/login')
def login():
    if session.get('user_id', None) is None:
        return github.authorize()
    else:
        return 'Already logged in'


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


@app.route('/user')
def user():
    return jsonify(github.get('/user'))


@app.route('/repo')
def repo():
    _user = User.get_one(args={'github_id': session.get('user_id')}, ffilter={'_id': 0})

    # filename = 'test.py'
    # branch = 'master'
    # token = _user.github_access_token
    #
    # url = "https://api.github.com/repos/{}/contents/{}".format(repo, filename)
    #
    # base64content = base64.b64encode(open(filename, "rb").read())
    #
    # data = requests.get(url + '?ref=' + branch, headers={"Authorization": "token " + token}).json()
    # print data
    # sha = data['sha']
    #
    # if base64content.decode('utf-8') + "\n" != data['content']:
    #     message = json.dumps({"message": "update",
    #                           "branch": branch,
    #                           "content": base64content.decode("utf-8"),
    #                           "sha": sha
    #                           })
    #
    #     resp = requests.put(url, data=message,
    #                         headers={"Content-Type": "application/json", "Authorization": "token " + token})
    #
    #     print(resp)
    # else:
    #     print("nothing to update")

    # for repo in Github(_user.github_access_token).get_user().get_repos():
    #     print(repo.name)

    try:
        return jsonify(github.get('/user/repos'))
    except Exception as e:
        print str(e)
        for repo in g.get_user().get_repos():
            print(repo.name)
        return 'hi'


@app.route('/pushFile')
def pushFile():
    # hello_world
    _user = User.get_one(args={'github_id': session.get('user_id')}, ffilter={'_id': 0})
    token = _user.github_access_token
    owner = _user.github_login
    _g = Github(_user.github_access_token)
    try:
        # filename = 'hello.py'
        filename = 'test2.py'
        # branch = 'master'
        # /repos/:owner/:repo/contents/:path
        url = "https://api.github.com/repos/{owner}/{repo}/contents/{path}".format(
            owner=owner, repo='kidogit', path=filename
        )
        base64content = base64.b64encode(open(filename, "rb").read())

        res = requests.get(url, headers={"Authorization": "token " + token})
        if res.status_code != 200:
            ''' new file to push '''
            message = json.dumps(
                {
                    "message": "test2.py added",
                    "content": base64content.decode("utf-8")
                }
            )
            res = requests.put(url, data=message,
                               headers={"Content-Type": "application/json", "Authorization": "token " + token})
            print res.json()
            return jsonify(message=res.json())

        else:
            data = requests.get(url, headers={"Authorization": "token " + token}).json()
            pprint.pprint(data)
            sha = data['sha']
            if base64content.decode('utf-8') + "\n" != data['content']:
                message = json.dumps(
                    {
                        "message": "push new changes",
                        "content": base64content.decode("utf-8"),
                        "sha": sha
                    }
                )
                res = requests.put(url, data=message,
                                   headers={"Content-Type": "application/json", "Authorization": "token " + token})
                print res.json()
                return jsonify(message=res.json())
            else:
                print("nothing to update")
                return jsonify(message="nothing to update")


        # for repo in Github(_user.github_access_token).get_user().get_repos():
        #     print(repo.name)

        # base64content = base64.b64encode(open('test.py', "rb").read())

        # repo = _g.get_repo("ntohidi/kidogit")
        # res = repo.create_file(
        #     path="test.py",
        #     message="test commit",
        #     content=base64content.decode("utf-8")
        # )

        # print res.json()
        # return jsonify(message=res.json())
    except Exception as e:
        print str(e)
        return jsonify(message='Error! ' + str(e))

    # bdy = {
    #     "name": "Hello-kido",
    #     "description": "This is your first repository",
    #     "homepage": "https://github.com",
    #     "private": False,
    #     "has_issues": True,
    #     "has_projects": True,
    #     "has_wiki": False
    # }
    # try:
    #     # log = github.post(resource='/user/repos', data=bdy)
    #     log = requests.post(
    #         "https://api.github.com/user/repos",
    #         {"data": bdy},
    #         headers={'Authorization': 'token ' + _user.github_access_token}
    #     )
    #     pprint.pprint(log.json())
    #     return jsonify(log.json())
    # except Exception as e:
    #     return jsonify(message='Error! ' + str(e))


if __name__ == '__main__':
    # init_db()
    app.run(host='0.0.0.0', port=9090, debug=True)
