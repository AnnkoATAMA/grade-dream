FROM node:latest

WORKDIR /front

COPY package.json ./

COPY . .

CMD ["sh", "-c", "test -d node_modules || npm install; npm start"]
