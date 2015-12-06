
// Set up WAMP connection to router
var connection = new autobahn.Connection({

   url: 'ws://192.168.1.11:8080/ws',
   realm: 'trapsensor'}

);

 // Enables the switchButton then sets 
   // its value then disables it again
   function trapstatus(ident, status) {
       document.getElementById(ident).disabled= false;
       $(document).ready(function(){
                  $('input[type=checkbox][id=' + ident + ']').switchButton({ checked: status});
              });
       document.getElementById(ident).disabled= true;

      }

   function setText(args) {
      // Set the text value of page elements
      macadrs.innerText = args.macadrs;
      macadrs.textContent = args.macadrs;
      date.innerText = args.datetime.dt;
      date.textContent = args.datetime.dt;
      time.innerText = args.datetime.tm;
      time.textContent = args.datetime.tm;
      volts.innerText = args.volts;
      volts.textContent = args.volts;
      //Set switchButton value - args[0].is_sprung is the trap status
      trapstatus("trap01",args.is_sprung );
   }


// Set up 'onopen' handler - runs when page refreshes
connection.onopen = function (session) {

   // code to execute on connection open goes here
  session.call('armote.trap.reedsensorLast').then(
      // RPC success callback - RPC passes return value in obj
      function (obj) {
         console.log("Call Success",obj);
         if (obj) {
           setText(obj);
        }
      },
      // RPC error callback
      function (error) {
         console.log("Call failed:", error);
      }
   );

};

// Open connection
connection.open();
