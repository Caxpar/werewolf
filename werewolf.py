from flask import Flask, request, render_template, redirect, url_for, session
from flask_socketio import SocketIO
from flask_socketio import send, emit
from datetime import timedelta
from enum import Enum
import random
from collections import defaultdict
from collections import Counter
import threading
import eventlet


class UserStatus(Enum):
    INIT = 0
    LIVE = 1
    DEAD = 2


class WWRole(Enum):
    UNKNOWN = 'role_unknown'
    WW = 'role_werewolf'
    VILLAGER = 'role_villager'
    SEER = 'role_seer'


class WWDescription(Enum):
    WAITTING = 'Waiting for starting.'
    DEAD = "Dead man can't speak."
    UNKNOWN_ROLE = "you don't have a role now."
    WW_ROLE = 'You can kill people at night.'
    VILLAGER_ROLE = 'You are really good man, sleep soundly at night.'
    SEER_ROLE = 'You can check the role of one user per night.'
    VILLAGER_NIGHT = 'Have a good night :)'
    WW_NIGHT = 'Start to kill others...'
    SEER_NIGHT = 'Click somebody to check his/her role...'
    DAY_TIME = 'Discuss and vote to suspecious ww'


class Actionable(Enum):
    DAY = 'day'
    NIGHT = 'night'
    ALL = 'all'
    NONE = 'none'


class User(object):
    def __init__(self, name, avatar, room):
        super().__init__()
        self.name = name
        self.room = room
        self.avatar = avatar
        # self.avatar_path = url_for('static', filename='images/' + avatar + '.png')
        self.avatar_path = 'static/images/' + avatar + '.png'
        self.refresh()
        self.user_card = render_template('user_card.html', name=name, role=self.role_avatar_url, avatar=self.avatar_path)
    
    def refresh(self, role=None):
        if not role:
            self.status = UserStatus.INIT
            self.role = WWRole.UNKNOWN
            self.role_description = WWDescription.UNKNOWN_ROLE.value
            self.description = WWDescription.WAITTING.value
            self.actionable = Actionable.NONE
            # self.role_path = url_for('static', filename='images/role_unknown.png')
            self.role_avatar_url = 'static/images/role_unknown.png'
        else:
            if role == WWRole.WW.value:
                self.role = WWRole.WW
                self.role_description = WWDescription.WW_ROLE.value
                self.actionable = Actionable.ALL
            elif role ==  WWRole.VILLAGER.value:
                self.role = WWRole.VILLAGER
                self.role_description = WWDescription.VILLAGER_ROLE.value
                self.actionable = Actionable.DAY
            elif role == WWRole.SEER.value:
                self.role = WWRole.SEER
                self.role_description = WWDescription.SEER_ROLE.value
                self.actionable = Actionable.ALL
            self.status =  UserStatus.LIVE
            # self.role_avatar_url = url_for('static', filename='images/' + role + '.png')
            self.role_avatar_url = 'static/images/' + role + '.png'
            print(self.role_avatar_url)


# Should split some logic to subclasses of User, such as vote.
class Game(object):
    def __init__(self):
        super().__init__()
        print('Game: ', '__init__')
        self.in_game = False
        self.is_night = False
        self.users = {}
        self.start_btn = ''
        self.role_cnt = {'werewolf_count': 3, 'villager_count': 3, 'seer_count': 1}
        self.day_time = 120
        self.night_time = 30
        self.votes = defaultdict(str)
        self.seer_checks = []

    def add_user(self, user_name, room):
        print('Game: ', 'add_user')

        # randomly generate a avatar
        avatar = 'Avatar_' + str(random.randint(1, 12))
        existing_user_avatars = [user.avatar for user in self.users.values()]
        while True:
            if avatar in existing_user_avatars and len(existing_user_avatars) < 12:
                avatar = 'Avatar_' + str(random.randint(1, 12))
            else:
                break

        # create a new user
        current_user = User(user_name, avatar, room)  # default role is unknown
        self.users[user_name] = current_user

        # show start button if this user is the first player
        if len(self.users) == 1:
            self.start_btn = user_name
            to_show_start_button(room, True)

        # add user card to this new user and other users
        for existing_user_name, existing_user in self.users.items():
            if not self.in_game:
                # add this new use to existing users
                to_add_user(current_user.user_card, user_name, existing_user.room)
            else:
                # if in game, only add current user to himself.
                to_add_user(current_user.user_card, user_name, current_user.room)

            # add existing user to new user
            if existing_user_name is not user_name:
                to_add_user(existing_user.user_card, existing_user_name, current_user.room)

        # set game role numbers to this new user
        for role, cnt in self.role_cnt.items():
            to_change_role_cnt(role, cnt, current_user.room)

    def remove_user(self, user_name):
        print('Game: ', 'remove_user')
        self.users.pop(user_name)
        if user_name == self.start_btn and len(self.users) > 0:
            self.start_btn = random.choice(list(self.users.keys()))
            to_show_start_button(self.users[self.start_btn].room, True)
        to_remove_user(user_name)

    def set_role_count(self, role, count):
        print('Game: ', 'set_role_count')
        if role == 'day_time':
            self.day_time = count
        elif role == 'night_time':
            self.night_time = count
        else:
            self.role_cnt[role] = count

    def start(self):
        self.in_game = True
        self.assign_roles()
        self.night_falls()
        to_show_start_button(self.users[self.start_btn].room, False)
    
    def tick_down(self, seconds):
        # print('tick_down, start time:', seconds)
        global app
        time_left = int(seconds)
        time_left -= 1
        to_tick_down(time_left)
        # print('tick_down:', time_left)
        if time_left > 0:
            self.timer = threading.Timer(1, self.tick_down, [time_left])
            self.timer.start()
        else:
            self.next_step()

    def next_step(self):
        self.vote_done()
        win = self.check_win()
        if win == 1:
            # to_win('villagers win!')
            to_tick_down('villagers win!')
            self.refresh()
        elif win == 2:
            to_tick_down('werewolves win!')
            self.refresh()
        else:
            if self.is_night:
                self.sun_rise()
            else:
                self.night_falls()

    def refresh(self):
        self.in_game = False
        self.is_night = False
        self.votes = defaultdict(str)
        self.seer_checks = []
        to_update_scene(day=True)
        to_hide_role()
        for name, user in self.users.items():
            to_show_role_avatar(name, user.role_avatar_url)
            if user.status is UserStatus.INIT:
                to_add_user(user.user_card, name)
        to_show_start_button(self.users[self.start_btn].room, True)
        self.refresh_users()
        self.refresh_actionable()
        self.refresh_description()
        self.refresh_vote()

    def sun_rise(self):
        self.is_night = False
        self.votes = defaultdict(str)
        to_update_scene(day=True)
        self.refresh_actionable()
        self.refresh_description()
        self.refresh_vote()
        self.tick_down(self.day_time)

    def night_falls(self):
        self.is_night = True
        self.votes = defaultdict(str)
        to_update_scene(day=False)
        self.refresh_actionable()
        self.refresh_description()
        self.refresh_vote()
        self.tick_down(self.night_time)

    def assign_roles(self):
        roles = []
        for role, count in self.role_cnt.items():
            for _ in range(int(count)):
                roles.append('role_' + role.split('_')[0])
        print(roles)
        print(self.users.keys())
        for name, user in self.users.items():
            if roles:
                c_role = random.choice(roles)  # current role
                roles.remove(c_role)
                user.refresh(role=c_role)
                to_assign_role(user)
                to_add_user(user.user_card, name)

    def refresh_users(self):  # re-init the game
        for name, user in self.users.items():
            user.refresh()

    def refresh_actionable(self):
        print('refresh_actionable')
        if self.is_night:  # night time
            for name, user in self.users.items():
                if user.status is UserStatus.DEAD:  # boradcast dead
                    to_update_actionable(name, False)
                elif user.status is UserStatus.LIVE:
                    # if live and actionable at night
                    if user.actionable is Actionable.ALL or user.actionable is Actionable.NIGHT:
                        # set all other alive users to actionable for this user
                        for to_name, to_user in self.users.items():
                            if to_user.status is UserStatus.LIVE:
                                to_update_actionable(to_name, True, user.room)
                        if user.role is WWRole.SEER:
                            to_update_actionable(name, False, user.room)  # seer can't check himself
                            for checked in self.seer_checks:  # seer shouldn't chech them again
                                to_update_actionable(checked, False, user.room)
                    else: # if live and not actionable at night
                        for to_name, to_user in self.users.items():
                            if to_user.status is UserStatus.LIVE:
                                to_update_actionable(to_name, False, user.room)
                else:
                    to_update_actionable(name, False)
                    
        else:  # day time
            for name, user in self.users.items():
                if user.status is UserStatus.INIT:  # game is not started
                    print(name, 'INIT')
                    to_update_actionable(name, False)
                    for a_name, a_user in self.users.items():
                        to_update_actionable(a_name, False, user.room)
                elif user.status is UserStatus.DEAD:
                    print(name, 'DEAD')
                    to_update_actionable(name, False)
                    for a_name, a_user in self.users.items():
                        to_update_actionable(a_name, False, user.room)
                else:
                    print(name, 'ALIVE')
                    for a_name, a_user in self.users.items():
                        if a_user.status is UserStatus.LIVE:
                            to_update_actionable(a_name, True, user.room)

    def refresh_description(self):
        for name, user in self.users.items():
            if user.status is UserStatus.DEAD:
                to_update_description(WWDescription.DEAD.value, user.room)
            elif user.status is UserStatus.INIT:
                to_update_description(WWDescription.WAITTING.value, user.room)
            else:
                if self.is_night:
                    if user.role is WWRole.SEER:
                        to_update_description(WWDescription.SEER_NIGHT.value, user.room)
                    elif user.role is WWRole.WW:
                        to_update_description(WWDescription.WW_NIGHT.value, user.room)
                    elif user.role is WWRole.VILLAGER:
                        to_update_description(WWDescription.VILLAGER_NIGHT.value, user.room)
                else:
                    to_update_description(WWDescription.DAY_TIME.value, user.room)

    def refresh_vote(self):
        for name, user in self.users.items():
            to_update_vote(name, 0)

    def vote(self, name, to_user_name):
        print(self.votes)
        user = self.users[name]
        to_user = self.users[to_user_name]
        if user.role is WWRole.SEER and self.is_night:
            self.seer_checks.append(to_user_name)
            to_show_role_avatar(to_user_name, to_user.role_avatar_url, user.room)
            to_set_selected(to_user_name, True, user.room)
            for name in self.users:
                to_update_actionable(name, False, user.room)
        else:
            if self.votes[name]:
                to_update_actionable(self.votes[name], True, user.room)
                to_set_selected(self.votes[name], False, user.room)
            self.votes[name] = to_user_name
            to_set_selected(to_user_name, True, user.room)
            to_update_actionable(to_user_name, False, user.room)
        cnts = Counter(self.votes.values())
        for name, user in self.users.items():
            cnt = 0
            if name in cnts:
                cnt = cnts[name]
            if self.is_night:
                for _ , ww in self.users.items():
                    if ww.role is WWRole.WW:
                        to_update_vote(name, cnt, ww.room)
            else:
                to_update_vote(name, cnt)
        print(self.votes)

    def vote_done(self):
        good_alive_man_cnt = 0
        bad_alive_man_cnt = 0
        for name, user in self.users.items():
            if user.status == UserStatus.LIVE:
                if user.role == WWRole.WW:
                    bad_alive_man_cnt += 1
                else:
                    good_alive_man_cnt += 1
        cnts = Counter(self.votes.values())
        if cnts:
            most_voted_user = max(cnts, key=self.votes.get)
            vote_cnt = cnts[most_voted_user]
            if not self.is_night and vote_cnt * 2 > good_alive_man_cnt:
                self.users[most_voted_user].status = UserStatus.DEAD
                to_kill_user(most_voted_user)
            elif self.is_night and vote_cnt * 2 > bad_alive_man_cnt:
                self.users[most_voted_user].status = UserStatus.DEAD
                to_kill_user(most_voted_user)

    def check_win(self): # 0, continue, 1: villager win, 2: ww win
        good_alive_man_cnt = 0
        bad_alive_man_cnt = 0
        for name, user in self.users.items():
            if user.status == UserStatus.LIVE:
                if user.role == WWRole.WW:
                    bad_alive_man_cnt += 1
                else:
                    good_alive_man_cnt += 1
        if bad_alive_man_cnt == 0:
            return 1
        if good_alive_man_cnt == 0:
            return 2
        return 0

eventlet.monkey_patch()
app = Flask(__name__)
app.send_file_max_age_default = timedelta(seconds=1)
app.secret_key = 'secret!'
socketio = SocketIO(app, async_mode = 'eventlet')
game = Game()
clients = {}

@socketio.on('connect')
def connect():
    name = session['name']
    print(request.namespace, request.sid)
    clients[name] = request.sid
    print('connect: ', name)

@socketio.on('disconnect')
def disconnect():
    print('disconnect: ', session['name'])
    session['login'] = False
    game.remove_user(session['name'])
    clients.pop(session['name'], None)

# webpages
@app.route('/', methods=['GET', 'POST'])
def login():
    print('main page called')
    if 'name' in request.form and 'pass' in request.form:
        name = request.form['name'].strip()
        pw = request.form['pass'].strip()
        if name and pw == 'lion':
            session['login'] = True
            session['name'] = name
            return redirect(url_for('main_game'))
        return redirect(url_for('login', res='wrong'))
    elif 'res' in request.args and request.args['res'] == 'wrong':
        return render_template('login.html', res=request.args['res'])
    else:
        return render_template('login.html')
    return render_template('login.html')

@app.route('/game')
def main_game():
    print('game page called')
    if 'login' not in session or not session['login']:
        return redirect(url_for('login'))
    return render_template('main.html')

# actions from the webpage
@socketio.on('add user')
def add_user(user):
    name = session['name']
    room = clients[name]
    game.add_user(name, room)

@socketio.on('start game')
def start_game():
    print('start_game')
    game.start()

@socketio.on('change role count')
def change_role_count(data):
    role = data['role']
    count = data['count']
    game.set_role_count(role, count)
    emit('change role count', data, broadcast=True)

@socketio.on('vote')
def vote(vote_data):
    print('received vote message: ', vote_data)
    name = session['name']
    to_user = vote_data['name']
    game.vote(name, to_user)

# actions to the webpage  
def to_show_start_button(room, show):
    print('to_show_start_button')
    socketio.emit("show start button", {'show': show}, room=room)

def to_change_role_cnt(role, cnt, room):
    print('to_set_role_cnt')
    socketio.emit('change role count', {'role':role, 'count':cnt}, room)

def to_add_user(div, user_name, room=None):
    print('to_add_user')
    if room:
        socketio.emit("add user", {'div':div, 'name': user_name}, room=room)
    else:
        socketio.emit("add user", {'div':div, 'name': user_name}, broadcast=True)

def to_update_actionable(user_name, actionable, room=None):
    print('to_set_actionable')
    if room:
        socketio.emit('update actionable', {'name': user_name, 'actionable': actionable}, room=room)
    else:
        socketio.emit('update actionable', {'name': user_name, 'actionable': actionable}, broadcast=True)

def to_remove_user(user_name):
    print('to_remove_user')
    socketio.emit('remove user', {"name":user_name}, broadcast=True)

def to_update_scene(day, room=None):
    if not room:
        socketio.emit('update scene', {'day':day}, broadcast=True)
    else:
        socketio.emit('update scene', {'day':day}, room=room)

def to_assign_role(user):
    socketio.emit('assign role', {'role': user.role.value, 'description':user.role_description, 'avatar':user.role_avatar_url}, room=user.room)

def to_hide_role():
    print('to_hide_role')
    socketio.emit('hide role', {}, broadcast=True)

def to_show_role_avatar(name, avatar, room=None):
    if room:
        socketio.emit('show role avatar', {'name': name, 'avatar': avatar}, room=room)
    else:
        socketio.emit('show role avatar', {'name': name, 'avatar': avatar}, broadcast=True)

def to_update_description(description, room=None):
    if room:
        socketio.emit('update description', {'description':description}, room=room)
    else:
        socketio.emit('update description', {'description':description}, broadcast=True)

def to_set_selected(name, is_selected, room):
    socketio.emit('set selected', {'name': name, 'selected':is_selected}, room=room)

def to_update_vote(name, count, room=None):
    if room:
        socketio.emit('update vote', {'name': name, 'count': count}, room=room)
    else:
        socketio.emit('update vote', {'name': name, 'count': count}, broadcast=True)

def to_kill_user(name):
    socketio.emit('kill user', {'name': name}, broadcast=True)

def to_tick_down(time):
    socketio.emit('tick down', {'time': time}, broadcast=True)

def to_win(info):
    socketio.emit('win', {'info':info}, broadcast=True)


if __name__ == '__main__':
    print('werewolf server start')
    # app.run(host='0.0.0.0', debug=False, port=5001)
    socketio.run(app, host='0.0.0.0',debug=True, port=5001)