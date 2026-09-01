/**
 * Тексты интерфейса по-английски.
 *
 * Перевод, а не пересказ: смысл и тон те же, что в русском словаре — на «ты»,
 * без рекламных обещаний, короткими фразами. Где буквальный перевод звучит
 * казённо, взята привычная английская формулировка.
 *
 * Названия мест, правовые документы и письма сервера пока остаются русскими.
 *
 * Структура повторяет ru.ts дословно: тип не даст ни пропустить ключ, ни
 * добавить лишний.
 */

import type { Dictionary } from "~/i18n/dictionary";

export const en: Dictionary = {
  language: {
    label: "Language",
    switchTo: "Русский",
  },

  app: {
    restoring: "Restoring your session…",
    toGame: "Back to the game",
    setupHint: "Set up your game and hit Start",
    quitConfirm: "End this game early?",
  },

  topbar: {
    round: (index, total) => `Round ${String(index)} of ${String(total)}`,
    progress: "Game progress",
    logout: "Log out",
    quit: "End game",
  },

  footer: {
    players: (count) => `${String(count)} ${count === 1 ? "player" : "players"} on board`,
    write: "Email us",
    source: "Source code",
    navLabel: "About the game and documents",
    creditsBefore: "Map and country borders — ©",
    creditsAfter: "contributors",
  },

  notice: {
    label: "About browser storage",
    text: "We set no cookies — the browser only keeps your login token.",
    details: "Details",
    ok: "Got it",
  },

  legal: {
    tabs: { terms: "Terms", privacy: "Privacy", storage: "Cookies" },
    list: "Documents",
    close: "Close",
    revision: (date) => `Revision of ${date}`,
    russianOnly: "The legal documents are in Russian only. Ask us if you need a translation.",
  },

  auth: {
    login: "Log in",
    register: "Sign up",
    email: "Email",
    password: "Password",
    passwordPlaceholder: (min) => `At least ${String(min)} characters`,
    displayName: "Name on the leaderboard",
    displayNameHint: "optional",
    displayNamePlaceholder: "How to show you",
    acceptBefore: "I accept the",
    acceptTerms: "terms of use",
    acceptAnd: "and the",
    acceptPrivacy: "privacy policy",
    submitLogin: "Log in",
    submitRegister: "Create account",
    noAccount: "No account yet?",
    goRegister: "Sign up",
    quick: " — takes half a minute",
    onlyEmail: "Only an email and a password. We send no letters and share the address with no one",
    fillBoth: "Fill in the email and the password",
    tooShort: (min) => `The password must be at least ${String(min)} characters`,
    mustAccept: "To create an account you need to accept the terms",
  },

  landing: {
    eyebrow: "A geoguesser on satellite imagery",
    titleTop: "Find the spot",
    titleBottom: "on the planet",
    lead:
      "You get a square of satellite imagery — no labels, no signs, no coordinates. Find that " +
      "place on the world map. The closer to the centre of the square, the more points.",
    play: "Play for free",
    how: "How it works",
    honest: "No ads, no trackers, no cookies. Seriously.",

    howTitle: "How a round goes",
    steps: [
      {
        title: "You look at the image",
        text: "A square of satellite imagery with no labels, road signs or coordinates. You can zoom in four levels — down to roofs and cars in the yard.",
      },
      {
        title: "You drop a pin",
        text: "Open the world map and mark the place where you think the square was shot. Missing by a continent is fine: there is another round.",
      },
      {
        title: "You get points",
        text: "The closer your pin is to the real centre of the square, the more points — up to five thousand per round.",
      },
    ],

    modesTitle: "What to play",
    modes: [
      {
        title: "Daily challenge",
        text: "Five rounds, the same for everyone, one attempt a day. By the evening you can see who was closest.",
      },
      {
        title: "Rooms for friends",
        text: "Create a room and send the link around. Everyone plays the same rounds and compares results in one table.",
      },
      {
        title: "Leaderboard",
        text: "Five separate standings: best game, total points, average miss, sharp rounds and games played.",
      },
    ],

    fairEyebrow: "How hard it gets",
    fairTitle: "You decide",
    fairText:
      "Easy gives you places you know by their outline — Paris, Venice, Manhattan. Normal is " +
      "large cities of familiar countries: Hamburg, Kazan, Seattle. Then come cities few people " +
      "know, and fields without a single sign. Hardcore leaves mountains, deserts and taiga: no " +
      "roads, no houses, only relief and the colour of the ground.",
    scorePerRound: "Points per round",
    placesInGame: "Places in the game",
    zoomLevels: "Zoom levels",

    faqTitle: "Frequently asked",
    questions: [
      {
        question: "What does it cost?",
        answer:
          "Nothing. There are no paid features, no ads, and we do not sell player data. The game is a pet project and it is open source.",
      },
      {
        question: "Do I have to sign up?",
        answer:
          "Yes, an email and a password. Without an account there is nowhere to keep your game history and no point in a leaderboard. We send no letters; the address is only for logging in.",
      },
      {
        question: "What do you do with my data?",
        answer:
          "We keep the email, a password hash, the name for the table and your game results. There is no analytics and no trackers on the page, and we set no cookies. The account is deleted by one button along with all of it.",
      },
      {
        question: "Where do the places come from?",
        answer:
          "From a list of places around the world: cities, coastlines, mountains, deserts and islands — almost three hundred areas on every continent. The point inside an area is picked at random, so the same city looks different every time.",
      },
      {
        question: "How is this different from other geoguessers?",
        answer:
          "Here you get a satellite image from above, not a street panorama: no shop signs, no licence plates, no language on the road signs. You have to read the shape of the buildings, the relief, the rivers and the shadows.",
      },
    ],

    finishTitle: "Shall we see how well you know the Earth?",
    finishCta: "Start playing",
  },
};
