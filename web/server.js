require('dotenv').config();
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
app.set('view engine', 'ejs');
app.use(express.static('public'));

app.use('/api', createProxyMiddleware({ target: process.env.API_URL + '/api', changeOrigin: true }));
app.use('/media', createProxyMiddleware({ target: process.env.API_URL + '/media', changeOrigin: true }));

const page = (view, title) => (req, res) => res.render(view, { title });

app.get('/',                  page('movies',  'Movies'));
app.get('/login',             page('login',   'Login'));
app.get('/movie/:id',         (req, res) => res.render('movie',     { title: 'Movie',     movieId: req.params.id }));
app.get('/movie/:id/shows',   (req, res) => res.render('showtimes', { title: 'Showtimes', movieId: req.params.id }));
app.get('/shows/:id',         (req, res) => res.render('seats',     { title: 'Select seats', showId: req.params.id }));
app.get('/tickets',           page('tickets', 'My tickets'));
app.get('/staff',             page('staff',   'Counter'));

app.listen(process.env.PORT, () =>
  console.log(`Web running at http://localhost:${process.env.PORT}`));