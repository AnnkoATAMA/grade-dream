FROM node:latest

WORKDIR /front

COPY package.json ./

RUN yarn install

COPY . .

CMD ["yarn", "start"]
