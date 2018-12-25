var http = require('http');

var express = require('express');
var path = require('path');
var cookieParser = require('cookie-parser');
var bodyParser = require('body-parser');
var logger = require('morgan');

var app = express();

app.use(function (req, res, next) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PATCH, PUT, DELETE, OPTIONS');
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === 'OPTIONS') return res.end();
  next();
});

app.use(logger('dev'));
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({extended: false}));
app.use(cookieParser());
app.use('/analyze', require('./api/analyze/analyze.route'))

var port = 3000
app.set('port', port);
var server = http.createServer(app);

// catch 404 and forward to error handler
app.use(function (req, res, next) {
  res.end({code: 999, message: 'API NOT FOUND'})
});


server.listen(port);
