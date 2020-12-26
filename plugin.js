console.log("seatalk remote plugin loaded");


/**
 * a widget that demonstrates how a widget from a plugin can interact with the python part
 * the widget will display the number of received nmea records
 * with a reset button the counter in the plugin at the python side can be reset
 *
 */
var widgetServer={
    name:"SeaTalkRemote",
    /**
     * if our plugin would like to use event handlers (like button click)
     * we need to register handler functions
     * this can be done at any time - but for performance reasons this should be done
     * inside an init function
     * @param context - the context - this is an object being the "this" for all other function calls
     *                  there is an empty eventHandler object in this context.
     *                  we need to register a function for every event handler we would like to use
     *                  later in renderHtml
     */
    initFunction:function(context){
        context.hasRmb=false;
        context.connected=false;
        //query the status from the server every second
        //trigger a redraw if changed
        context.timer=window.setInterval(function(){
            fetch(AVNAV_BASE_URL+"/api/status")
                .then(function(data){return data.json();})
                .then(function(status){
                    var isChanged=false;
                    if (context.hasRmb !== status.hasRmb || context.connected !== status.connected){
                        context.connected=status.connected;
                        context.hasRmb=status.hasRmb;
                        context.triggerRedraw();
                    }
                })
        },1000);

        var statusDisplay=function(ok){
            context.commandOk=ok;
            context.triggerRedraw();
            window.setTimeout(function(){
                context.commandOk=undefined;
                context.triggerRedraw();
            },800);
        }
        /**
         * each event handler we register will get the event as parameter
         * when being called, this is pointing to the context (not the event target - this can be obtained by ev.target)
         * in this example we issue a request to the python side of the plugin using the
         * global variable AVNAV_BASE_URL+"/api" and appending a further url
         * We expect the response to be json
         * @param ev
         */
        context.eventHandler.buttonClick=function(ev){
            //we have the key we would like to send in a data-key attribute at the button
            var key=ev.target.getAttribute('data-key');
            if (! key) return;
            fetch(AVNAV_BASE_URL+"/api/key"+key)
                .then(function(data){
                    return data.json();
                })
                .then(function(json)
                {
                    if (json.status !== 'OK'){
                        //TODO some error handling
                        statusDisplay(false);
                    }
                    else{
                        statusDisplay(true);
                    }
                })
                .catch(function(error){
                    statusDisplay(false);
                    avnav.api.showToast("ERROR: "+error)}
            );
        };
    },

    finalizeFunction:function(context){
        //stop the query to the server
        window.clearInterval(context.timer);
    },
    /**
     * a function that will render the HTML content of the widget
     * normally it should return a div with the class widgetData
     * but basically you are free
     * If you return null, the widget will not be visible any more.
     * @param props
     * @returns {string}
     */

    renderHtml:function(props){
        /**
         * in our html below we assign an event handler to the buttons
         * just be careful: this is not a strict W3C conforming HTML syntax:
         * the event handler is not directly js code but only the name(!) of the registered event handler.
         * it must be one of the names we have registered at the context.eventHandler in our init function
         * Unknown handlers or pure java script code will be silently ignored!
         */
        //as we are not sure if the browser supports template strings we use the AvNav helper for that...
        var template='<div class="widgetData">' +
            '<div class="buttonRow">'+
            '<button class="remote m1" data-key="m1" onclick="buttonClick">-1</button>' +
            '<button class="remote p1" data-key="p1" onclick="buttonClick">+1</button>' +
            '</div>'+
            '<div class="buttonRow">'+
            '<button class="remote m10" data-key="m10" onclick="buttonClick">-10</button>' +
            '<button class="remote p10" data-key="p10" onclick="buttonClick">+10</button>' +
            '</div>'+
            '<div class="buttonRow">'+
            '<button class="remote A" data-key="A" onclick="buttonClick">A</button>' +
            '<button class="remote S" data-key="S" onclick="buttonClick">S</button>' +
            '</div>'+
            '<div class="statusRow">'+
            '<span class="statusText connected">Connected</span>'+
            '<span class="statusItem connected ${connected}"></span>'+
            '<span class="statusCommand ${command}"></span>'+
            '<span class="statusItem hasRmb ${hasRmb}"></span>'+
            '<span class="statusText hasRmb">hasRmb</span>'+
            '</div>'+
            '</div>';
        var replacements={
            connected:this.connected?'yes':'no',
            hasRmb:this.hasRmb?'yes':'no',
            command:this.commandOk?'yes':(this.commandOk === undefined)?'empty':'no'
        };

        return avnav.api.templateReplace(template,replacements);
    },
    caption: "Seatalk Remote",
    unit: ""
};

avnav.api.registerWidget(widgetServer);
avnav.api.log("testPlugin widgets registered");
