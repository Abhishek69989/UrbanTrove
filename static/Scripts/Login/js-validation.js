function ValidateEmail(inputText)
{
    var mailformat = /^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$/;
    if(inputText.value.match(mailformat))
    {
        document.querySelector(".js-email-error").innerHTML='';
        return true;
    }
    else
    {
        document.querySelector(".js-email-error").innerHTML='<p>Invalid Email</p>';
        return false;
    }
}


function ValidatePassword(inputPass){
    if(inputPass.length>8){
        document.querySelector(".js-pass-error").innerHTML='';
        return true;
    }
    else{
        document.querySelector(".js-pass-error").innerHTML='<p>Invalid Password</p>';
        return false;
    }
    
}

function Validation(inputText,inputPass){
    return ValidateEmail(inputText)&&ValidatePassword(inputPass);
}