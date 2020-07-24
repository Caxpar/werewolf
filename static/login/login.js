function show_con(x, did){
    var con= document.getElementById(did);
    if(x<1){
        x=x+0.02;
        con.style.opacity=x;
        window.setTimeout(function(){show_con(x, did)},10);
    }else{
        log_btn = document.getElementById('login_btn')
        log_btn.innerHTML = 'Play'
        return;
    }
}

function do_submit(){
    document.getElementById("login_form").submit();
}

function show_login(did) {
    log_btn = document.getElementById('login_btn')
    if(log_btn.innerHTML == 'Play'){
        do_submit()
    }else{
        show_con(0.0, did);
    }
}
document.onkeydown = function(event_e){  
    if(window.event) {  
        event_e = window.event;  
    }  
    var int_keycode = event_e.charCode||event_e.keyCode;  
    if( int_keycode == '13' ) {  
        log_btn = document.getElementById('login_btn')
        if(log_btn.innerHTML == 'Play'){
            do_submit()
            return false;  
        }        
    }  
}; 