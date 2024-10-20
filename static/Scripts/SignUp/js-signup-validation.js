function Empty(inputname,inputAddress,inputText,inputPass,inputrepass,number){
    if(inputname==''||inputText.value==''||inputPass==''||inputrepass==''||inputAddress==''||number==''){
        document.querySelector(".error").innerHTML='<p>Fill up all credentials</p>';
        return false;
    }
    else{
        document.querySelector(".error").innerHTML='';
        return true;
    }
}


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
        document.querySelector(".js-pass-error").innerHTML='<p>Password must contain 8 or more words.</p>';
        return false;
    }
    
}
function matchPass(inputPass,inputrepass) 
      {
        if(inputPass==inputrepass)
        {
            document.querySelector(".js-pass-error").innerHTML='';
            return true;
        }
        else
        {
            document.querySelector(".js-re-pass-error").innerHTML='<p>Passwords does not match.</p>';
            return false;
        }
      }

function Mobile(number) {
    if(number>999999999&&number<10000000000){

            document.querySelector(".js-mobile-error").innerHTML='';
            return true;
    } else{
        document.querySelector(".js-mobile-error").innerHTML='Invalid mobile number.';
        return false;
    }
}


function Validation(inputname,inputAddress,inputText,inputPass,inputrepass,number){
    return Empty(inputname,inputAddress,inputText,inputPass,inputrepass,number)&&ValidateEmail(inputText)&&ValidatePassword(inputPass)&&matchPass(inputPass,inputrepass)&&Mobile(number);
}