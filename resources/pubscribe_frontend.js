
try {
   var autobahn = require('autobahn');
} catch (e) {
   // when running in browser, AutobahnJS will
   // be included without a module system
}

var connection = new autobahn.Connection({
   url: 'ws://192.168.1.11:8080/ws',
   realm: 'trapsensor'}
);

connection.onopen = function (session) {

   // Enables the switchButton then sets 
   // its value then disables it again
   function trapstatus(ident, status) {
       document.getElementById(ident).disabled= false;
       $(document).ready(function(){
                  $('input[type=checkbox][id=' + ident + ']').switchButton({ checked: status});
              });
       document.getElementById(ident).disabled= true;

      }

   // var received = 0;
   // Get page elements
   var macadrs = document.getElementById("macadrs");
   var date = document.getElementById("date");
   var time = document.getElementById("time");
   var volts = document.getElementById("volts");

   // function fires on data received event
   function onevent1(args) {
      console.log("Got event:", args[0]);
      // Set the text value of page elements
      macadrs.innerText = args[0].macadrs;
      macadrs.textContent = args[0].macadrs;
      date.innerText = args[0].datetime.dt;
      date.textContent = args[0].datetime.dt;
      time.innerText = args[0].datetime.tm;
      time.textContent = args[0].datetime.tm;
      volts.innerText = args[0].volts;
      volts.textContent = args[0].volts;
      //Set switchButton value - args[0].is_sprung is the trap status
      trapstatus("trap01",args[0].is_sprung );
      // received += 1;
      // if (received > 5) {
      //    console.log("Closing ..");
      //    connection.close();
      // }
   }

   session.subscribe('armote.trap.reedsensor', onevent1);
};

connection.open();
