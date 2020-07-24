var socket = io();

socket.on('connect', function () {
    console.log("on connect");
    socket.emit('add user', {})
});

socket.on('update description', function (data) {
    console.log("update description: " + data);
    var con = document.getElementById('description');
    con.innerHTML = data.description;
});

socket.on('add user', function (data) {
    console.log("on my response");
    mainGameDiv = document.getElementById('main');
    var div_id = data['name'] + "_card";
    if (document.getElementById(div_id) != null) {
        document.getElementById(div_id).remove();
    }
    console.log("add user: " + data['name']);
    mainGameDiv.innerHTML += data['div'];
    show_con(0, div_id);
});

socket.on('remove user', function (data) {
    console.log("on remove user");
    var div_id = data['name'] + "_card";
    if (document.getElementById(div_id) != null) {
        document.getElementById(div_id).remove();
    }
});

socket.on('kill user', function (data) {
    console.log("kill user: " + data.name);
    var con = document.getElementById(data.name + '_card_dead');
    console.log(con);
    con.style.display = 'unset';
    show_con(0, data.name + '_card_dead');
});

socket.on('show start button', function (data) {
    console.log("show start button" + data);
    console.log(data);
    var start_btn = document.getElementById('start_game_btn');
    if (data.show) {
        start_btn.style.display = '';
    } else {
        start_btn.style.display = 'none';
    }
});

socket.on('update scene', function (data) {
    console.log("update scene" + data);
    change_day_night(data.day);
});

socket.on('assign role', function (data) {
    console.log('assign role');
    var role_description_div = document.getElementById('role_description_div');
    var role_description = document.getElementById('role_description');
    var role_avatar = document.getElementById('role_avatar');
    // console.log(role_description_div);
    // console.log(role_description);
    // console.log(role_avatar);
    role_description_div.style.display = 'unset';
    role_description.innerHTML = data.description;
    role_avatar.src = data.avatar;
});

socket.on('show role avatar', function (data) {
    console.log('show role avatar');
    var card_role_avatar = document.getElementById(data.name + '_card_role');
    card_role_avatar.src = data.avatar;
});

socket.on('change role count', function (data) {
    console.log("change role count" + data);
    var changed_role = data.role;
    var changed_count = data.count;
    var input_element = document.getElementById(changed_role);
    input_element.value = changed_count;
});

socket.on('update actionable', function (data) {
    var name = data.name;
    var actionable = data.actionable;
    change_actionable(name, actionable);
});

socket.on('set selected', function (data) {
    var name = data.name;
    var selected = data.selected;
    var con = document.getElementById(name + "_card");
    if (selected) {
        con.style.backgroundColor = 'rgb(187, 63, 63)';
    } else {
        con.style.backgroundColor = 'rgb(179, 179, 179)';
    }
    
});

socket.on('tick down', function (data) {
    var time = data.time;
    var con = document.getElementById("timer");
    con.innerHTML = time;
    
});

socket.on('hide role', function (data) {
    console.log('hide role')
    var role_description_div = document.getElementById('role_description_div');
    role_description_div.style.display = 'none';
});

socket.on('update vote', function (data) {
    console.log("update vote: " + data.name + ", cnt: " + data.count);
    var name = data.name;
    var votes = parseInt(data.count, 10);
    var count_div = document.getElementById(name + '_card_vote');
    var knife_div = document.getElementById(name + '_card_knife');
    if (votes == 0) {
        console.log('vote == 0');
        count_div.style.display = 'none';
        knife_div.style.display = 'none';
    } else {
        count_div.style.display = 'unset';
        knife_div.style.display = 'unset';
    }
    count_div.innerHTML = votes;
});

socket.on('win', function (data) {
    alert(data.info);
});

function show_con(x, did) {
    var con = document.getElementById(did);
    if (x < 1) {
        x = x + 0.02;
        con.style.opacity = x;
        window.setTimeout(function () { show_con(x, did) }, 10);
    }
}

// when night is coming
function change_bg_black(x) {
    var con = document.getElementById("bg");
    // console.log("change_bg_black: " + x);
    if (x < 1) {
        x = x + 0.02;
        con.style.backgroundColor = 'rgba(0, 0, 0, ' + x + ')';
        window.setTimeout(function () { change_bg_black(x) }, 20);
    }
}

// when day is coming
function change_bg_white(x) {
    var con = document.getElementById("bg");
    if (x > 0) {
        x = x - 0.02;
        con.style.backgroundColor = 'rgba(0, 0, 0, ' + x + ')';
        window.setTimeout(function () { change_bg_white(x) }, 20);
    }
}

// change user card to clickable or not
function change_actionable(user_name, actionable) {
    console.log("change_actionable: " + user_name + ', ' + actionable);
    var name = user_name + '_card';
    var con = document.getElementById(name);
    if (actionable) {
        con.style.pointerEvents = 'unset';
    } else {
        con.style.pointerEvents = 'none';
    }
    
}

function on_card_click(e, name) {
    socket.emit('vote', {name: name});
}

function start_game() {
    socket.emit('start game')
}

function set_role_number(e, role) {
    socket.emit('change role count', {role: role, count: e.target.value})
}

function vote_done() {
    var con = document.getElementById("bg");
    var day = 1;
    if (con.style.backgroundColor.length < 15) {
        day = 0;
    }
    socket.emit('vote done', {day: day})
}

function change_day_night(day) {
    console.log('change_day_night: ' + day);
    var names = document.getElementsByClassName('user_card_name');
    // console.log(names);
    if (day) {
        change_bg_white(1);
        for (i = 0; i < names.length; i++) {
            names[i].style.color = '#000';
        }
    } else {
        change_bg_black(0)
        for (i = 0; i < names.length; i++) {
            names[i].style.color = '#fff';
        }
    }
}


// only for testing
function add_user() {
    // var name = sessionStorage.getItem('name');
    var name = 'user_' + Math.floor(Math.random() * 100);;
    console.log(name);
    socket.emit('add user', { name: name })
}
