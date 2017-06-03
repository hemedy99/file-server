(function() {
  var ERROR_THRESHOLD, MAX_DISTANCE, canvas, ctx, keepPredicting, onError, onPredictClose, onSuccess, onTrainClose, predict, setupWS, showFace, train, update, updateProgressBar, video,
    _this = this;

  onError = function(e) {
    return console.log("Rejected", e);
  };

  onSuccess = function(localMediaStream) {
    video.src = window.URL.createObjectURL(localMediaStream);
    return setInterval(update, 250);
  };

  setupWS = function(url, close) {
    var _ref;
    if ((_ref = window.ws) != null) {
      _ref.close();
    }
    window.ws = new WebSocket("ws://" + location.host + "/" + url);
    window.ws.onopen = function() {
      return console.log("Opened websocket " + url);
    };
    return window.ws.onclose = close;
  };

  update = function() {
    ctx.drawImage(video, 0, 0, 320, 240);
    return canvas.toBlob(function(blob) {
      var _ref;
      return (_ref = window.ws) != null ? _ref.send(blob) : void 0;
    }, 'image/jpeg');
  };

  MAX_DISTANCE = 1000;

  ERROR_THRESHOLD = 10;

  video = document.querySelector('video');

  canvas = document.querySelector('canvas');

  ctx = canvas.getContext('2d');

  ctx.strokeStyle = '#ff0';

  ctx.lineWidth = 2;

  predict = function() {
    var errorCounter,
      _this = this;
    console.log('Started to predict');
    errorCounter = 0;
    return window.ws.onmessage = function(e) {
      var data, debugArea;
      data = JSON.parse(e.data);
      $('#predict').show();
      if (data) {
        debugArea = $('.prettyprint');
        debugArea.text(JSON.stringify(data, void 0, 2));
        debugArea.append("\n\nError counter: " + errorCounter);
        $('#name-of-face').text("Hello " + data.face.name + "!");
        if (showFace()) {
          ctx.strokeRect(data.face.coords.x, data.face.coords.y, data.face.coords.width, data.face.coords.height);
        }
        if (data.face.distance < MAX_DISTANCE && errorCounter > ERROR_THRESHOLD * -1) {
          errorCounter -= 1;
        } else {
          errorCounter += 1;
        }
        if (errorCounter > ERROR_THRESHOLD && !keepPredicting()) {
          console.log("About to close predict websocket");
          errorCounter = 0;
          return window.ws.close();
        }
      }
    };
  };

  showFace = function() {
    return $('#show-face').attr('checked');
  };

  keepPredicting = function() {
    return $('#keep-predicting').attr('checked');
  };

  train = function() {
    var saveLabel, startHarvest;
    console.log('Started training');
    $('#name').val("");
    $('#predict').hide();
    $('#train').show();
    $('#input').show();
    startHarvest = function() {
      setupWS('harvesting', onTrainClose);
      return window.ws.onmessage = function(e) {
        console.log("closing harvesting websocket");
        window.ws.close();
        return updateProgressBar(70, 'Training model');
      };
    };
    saveLabel = function(label) {
      console.log("Saving " + label);
      $('#input').hide();
      $('#training').show();
      updateProgressBar(40, 'Saving label');
      return $.post('/enrol', {
        label: label
      }).success(function() {
        updateProgressBar('50');
        return startHarvest();
      });
    };
    return $('#start').click(function(e) {
      var label;
      e.preventDefault();
      label = $('#name').val();
      if (label) {
        return saveLabel(label);
      }
    });
  };

  updateProgressBar = function(w, text) {
    if (text == null) {
      text = 'Saving images';
    }
    $('.bar').css('width', "" + w + "%");
    return $('.bar').text(text);
  };

  onPredictClose = function(e) {
    console.log('About to start training');
    $('#predict').hide();
    return train();
  };

  onTrainClose = function(e) {
    return $.post('/train').success(function() {
      console.log("done training");
      updateProgressBar(100);
      $('#training').hide();
      setupWS('predict', onPredictClose);
      return predict();
    });
  };

  navigator.mozGetUserMedia({
    'video': true,
    'audio': false
  }, onSuccess, onError);

  setupWS('predict', onPredictClose);

  predict();

}).call(this);
