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

  game: {
    toTarget: "To target",
    toNorth: "North up",
    keysMap: "map",
    keysAnswer: "answer",
    keysZoom: "reset zoom",
    keysNorth: "north up",
    frame: (size) => `about ${size} across`,
    tilesFailed: "Part of the image did not load. Drag the map and the tiles will load again.",
    hint: "Hint",
    hintCost: (points) => `−${points} points`,
    secondsLeft: (seconds) => `Seconds left: ${String(seconds)}`,

    dropPin: "Mark the place on the world map",
    pinDropped: "Pin dropped",
    loadingCountries: "Loading countries…",
    pickCountry: "Pick the country the image comes from",
    collapse: "Collapse",
    pin: "Keep open",
    answer: "Answer",
    openCountries: "Pick a country",
    openMap: "Open the map",
    changePin: "Move the pin",

    choicesLabel: "Which country the image comes from",
    whichCountry: "Which country is this image from?",
    mayChange: "You can change your mind before answering",

    coachStep: (order, total) => `Step ${String(order)} of ${String(total)}`,
    coachGot: "Got it",
    coachSkip: "Do not show this",
    coach: {
      lookTitle: "Take a look",
      lookText:
        "This is a piece of satellite imagery with no labels or signs. The crosshair in the centre marks the place you need to find. Zoom with the wheel or a pinch, drag to look around.",
      chooseTitle: "Pick a country",
      chooseText:
        "Six countries are listed under the image, and one of them is where it was shot. Look for clues: vegetation, roofs, road markings, the language on signs when you zoom in.",
      chooseAnswer:
        "You can change your mind as long as you have not pressed Answer. Get it right and you take all five thousand points for the round; miss, and the closer your country is to the real one, the more you keep.",
      pinTitle: "Mark the place",
      countryHover:
        "Move the cursor to the world map in the bottom right corner and click the country you think the image is from. The country under the cursor is highlighted.",
      countryTap:
        "Tap “Pick a country” in the bottom right corner and tap the country on the world map you think the image is from.",
      pinHover:
        "Move the cursor to the world map in the bottom right corner and click where you think this piece was shot.",
      pinTap:
        "Tap “Open the map” in the bottom right corner and mark the place on the world map where you think this piece was shot.",
      answerTitle: "Answer",
      answerCountry:
        "Tap the country on the map the image is from. You can change it as long as you have not pressed Answer: get it right and you take all five thousand points for the round.",
      answerPin:
        "Tap the place on the map where you think the piece was shot. You can move the pin until you press Answer: the closer to the target, the more points — up to five thousand per round.",
    },

    resultLabel: "Round result",
    outOf: (max) => `of ${max} points`,
    country: "Country",
    yourAnswer: "Your answer",
    missedLand: "missed the land",
    miss: "Miss",
    accuracy: "Accuracy",
    usualMiss: (distance) => `People usually miss this one by ${distance} — `,
    youCloser: "you are closer",
    youFurther: "you are further",
    target: "target",
    yourPin: "your pin",
    seeSummary: "See the summary",
    nextRound: "Next round",

    gameOver: "Game over",
    points: "points",
    nothingPlayed: "Not a single round played",
    summary: (rounds, average) =>
      `${String(rounds)} ${rounds === 1 ? "round" : "rounds"} · ${average} per round on average`,
    record: "This is your best result",
    placeIn: (place) => `place ${String(place)} in`,
    showWholeGame: "Show the whole game",
    roundOfZone: (index, zone) => `Round ${String(index)}, ${zone}`,
    setUpGame: "Set up a game",
    playAgain: "Play again",
    toMenu: "To the menu",

    share: "Share the result",
    shareCopied: "Copied to the clipboard",
    shareFailed: "Could not copy",
    shareScore: (score) => `${score} points`,
    shareBest: (distance) => `Best round: ${distance}`,
    shareChallenge: (day) => `Location King · challenge of ${day}`,

    loadingRound: "Picking a place…",
    loadingDistance: "Measuring the distance…",
    loadingTimeout: "Time is up…",
    loadingSummary: "Adding it up…",
    noRound: "The server returned no round",

    tiers: {
      perfect: "Bullseye",
      great: "Excellent",
      good: "Good",
      fair: "Not bad",
      poor: "Off",
      awful: "Nowhere near",
    },

    avatarOf: (name) => `Avatar of ${name}`,
    avatar: "Player avatar",
    loading: "Loading",
  },

  room: {
    title: "Room",
    subtitle:
      "The same rounds for everyone who joins. You each play at your own pace and compare results.",
    fromSolo: "Conditions come from the single game:",
    editSetup: "Change the conditions",
    create: "Create a room",
    codePlaceholder: "CODE",
    codeLabel: "Room code",
    enter: "Join",
    mine: "Your rooms",
    players: (count) => `${String(count)} ${count === 1 ? "player" : "players"}`,
    leave: "Leave",
    meta: (rounds, time, host) =>
      `${String(rounds)} ${rounds === 1 ? "round" : "rounds"} · ${time} · host ${host}`,
    closed: " · closed for new players",
    copyLink: "Copy the link",
    linkCopied: "Link copied",
    copyFailed: "Could not copy",
    nobodyYet: "Nobody has joined yet. Send the link to your friends.",
    play: "Play",
    signupsClosed: "The room is closed — joining is no longer possible.",
    resume: "Continue the game",
    myScore: "Your result",
    closeSignups: "Close the room",
    notFound: "Room not found",
    createFailed: "Could not create the room",
    enterFailed: "Could not join the room",
    closeFailed: "Could not close the room",
  },

  board: {
    title: "Leaderboard",
    metric: "Metric",
    scope: "Standings",
    scopes: {
      all: "All games",
      friends: "Friends",
      easy: "Easy",
      normal: "Normal",
      hard: "Hard",
      hardcore: "Hardcore",
      russia: "Russia",
      usa: "USA",
      eu: "European Union",
    },
    metrics: {
      best: { label: "Game", hint: "Points per round in the best game" },
      total: { label: "Total", hint: "Points across all games" },
      accuracy: { label: "Accuracy", hint: "Average miss per round, from five rounds up" },
      sharp: { label: "Sharp", hint: "Rounds taken almost exactly" },
      games: { label: "Games", hint: "Games played to the end" },
    },
    emptyAll: "Nobody has played a single game yet. Take the first place",
    emptyFriends: "Neither you nor your friends have finished a game yet",
    emptyScope: "Nobody has played these conditions yet. Take the first place",
    failed: "Could not load the table",
  },

  profile: {
    title: "Profile",
    games: "Games",
    rounds: "Rounds",
    best: "Best game",
    averageMiss: "Average miss",
    rating: "Rating",
    theme: "Appearance",
    themeFailed: "Could not save the appearance",

    edit: "Edit",
    replacePicture: "Replace",
    removePicture: "Remove",
    uploadPicture: "Upload your own picture",
    cancel: "Cancel",
    save: "Save",
    name: "Name in the table",
    nameHint: (max) => `other players see it, up to ${String(max)} characters`,
    avatar: "Avatar",
    ownPicture: "Your own picture",
    ownPictureHint: "Other players see it in the tables and in the room",
    patterns: "Avatar pattern",
    pattern: (index) => `Pattern ${String(index)}`,
    colors: "Avatar colour",
    color: (index) => `Colour ${String(index)}`,
    tooHeavy: "The picture is heavier than four megabytes",
    uploadFailed: "Could not upload the picture",
    removeFailed: "Could not remove the picture",
    saveFailed: "Could not save",
  },

  friends: {
    title: "Friends",
    byCode: "Friends are added by player code — a name will not do",
    waiting: (count) => `${String(count)} ${count === 1 ? "request is" : "requests are"} waiting`,
    invite: "Invite",
    accept: "Accept",
    myCode: "Your code",
    copy: "Copy",
    copied: "Copied",
    friendCode: "Friend's code",
    empty: "Nobody yet. Swap codes and you will see a shared standing.",
    invitesYou: "invites you",
    awaitingAnswer: "waiting for an answer",
    remove: (name) => `Remove ${name}`,
    listFailed: "Could not read the friend list",
    inviteFailed: "Could not send the request",
    acceptFailed: "Could not accept the request",
    removeFailed: "Could not remove",
  },

  history: {
    title: "Recent games",
    empty: "You have not played a single game yet",
    rounds: (count) => `${String(count)} ${count === 1 ? "round" : "rounds"}`,
    status: { finished: "finished", abandoned: "dropped", active: "unfinished" },
  },

  feedback: {
    open: "Feedback",
    thanks:
      "I read everything. I cannot promise a personal reply, but fixes and new things come exactly from letters like this.",
    invitation: "Write plainly: what you liked, what annoys you, what does not work.",
    close: "Close",
    cancel: "Cancel",
    send: "Send",
    label: "Feedback about the game",
    title: "How do you like the game?",
    sent: "Got it, thank you",
    about: "About",
    kinds: { impression: "Impression", problem: "Problem" },
    hints: {
      impression: "What you liked and what you did not",
      problem: "What happened and on which screen",
    },
    message: "Message",
    left: (count) => `${String(count)} left`,
    empty: "Write what happened",
    failed: "Could not send",
  },

  deleteAccount: {
    open: "Delete the account",
    warning:
      "All your games, rounds, place on the leaderboard and rooms you created go with it. There will be nothing to restore it from.",
    cancel: "Cancel",
    confirm: "Delete for good",
    label: "Deleting the account",
    title: "Delete the account?",
    password: "Password",
    passwordPlaceholder: "Confirm it is you",
    needPassword: "Enter the password",
    failed: "Could not delete the account",
  },

  duel: {
    title: "Duel",
    subtitle: "Opponents are matched by rating",
    yourRating: "your rating",
    noDuelsYet: " · no duels yet",
    rulesUnknown: "The same rounds for both",
    rules: (rounds, time) =>
      `${String(rounds)} ${rounds === 1 ? "round" : "rounds"} · ${time} per round · the same places for both`,
    find: "Find an opponent",
    joining: "Opponent found…",
    cancel: "Cancel the search",
    lookingFor: "Looking for an opponent",
    found: "Opponent found",

    nobody: "Nobody is searching right now",
    onlyYou: "So far it is only you",
    searching: (others) =>
      `${String(others)} ${others === 1 ? "player is" : "players are"} looking for an opponent`,
  },

  daily: {
    title: "Daily challenge",
    subtitle: (rounds) =>
      `${String(rounds)} ${rounds === 1 ? "round" : "rounds"}, the same for everyone. One attempt a day.`,
    streak: (days) => `${days === 1 ? "day" : "days"} in a row`,
    keepStreak: " — play today to keep it going",
    bestStreak: (days) => ` · record ${String(days)}`,
    myResult: "Your result today",
    onlyYouPlayed: "You are the only one who has played so far",
    nobodyFinished: "Nobody has finished today yet",
    play: "Play the challenge",
    resume: "Continue the challenge",
    lost: "Today's game was dropped — another game replaced it. The challenge is back tomorrow.",
    failed: "Could not start the challenge",

    onceADay: "One attempt a day",
    playedStatus: (score) => `Played · ${score}`,
    unfinishedStatus: "Game unfinished",
    abandonedStatus: "Game dropped",
    freshStatus: "Not played today",
    streakStatus: (days) => `${String(days)} ${days === 1 ? "day" : "days"} in a row — keep it`,
  },

  setup: {
    answerMode: "How to answer",
    answerModes: {
      choice: {
        label: "One of six",
        hint: "Six countries under the image, one is right. The easiest way to start",
      },
      country: {
        label: "By country",
        hint: "A map with borders: hit it and take the maximum, miss and score by distance",
      },
      point: { label: "By pin", hint: "A pin on the world map, points for being close" },
    },

    level: "Difficulty",
    levels: {
      easy: { label: "Easy", hint: "Known by their outline: Paris, Venice, Manhattan" },
      normal: {
        label: "Normal",
        hint: "Large cities of familiar countries: Hamburg, Kazan, Seattle",
      },
      hard: {
        label: "Hard",
        hint: "Cities few people know, and inhabited land without a city",
      },
      hardcore: { label: "Hardcore", hint: "The wild: mountains, deserts, taiga, ice" },
    },

    place: "Where to play",
    places: {
      world: "Whole world",
      russia: "Russia",
      usa: "USA",
      eu: "European Union",
      europe: "Europe",
      asia: "Asia",
      africa: "Africa",
      northAmerica: "North America",
      southAmerica: "South America",
      oceania: "Oceania",
    },

    rounds: "Rounds",
    time: "Time per round",
    timeHint: "The faster you answer, the more points",

    zonesFound: (count) => `Places to draw from: ${String(count)}`,
    countryNote:
      "In country mode we play the whole world: a chosen place would hint at the answer.",
    noZones: "No places match these conditions. Take another level or another place.",
    start: "Start playing",

    soloTitle: "Single game",
    soloSubtitle: "Round after round, just you and the image",
    soloNewcomer:
      "Everything is set for your first game: five rounds over cities everyone knows. Just hit Start",
    landmarksTitle: "Famous places",
    landmarksSubtitle:
      "The Pyramids of Giza, the Colosseum, the Taj Mahal, Palm Jumeirah — close up, without the city around them",

    describeRounds: (count) => `${String(count)} ${count === 1 ? "round" : "rounds"}`,
    describeCountry: "answer by country",
    describeChoice: "one of six",
  },

  menu: {
    modes: "Game mode",
    sections: "Sections",
    section: {
      profile: "Profile",
      friends: "Friends",
      board: "Leaderboard",
      history: "History",
    },

    solo: "Single",
    landmarks: "Famous places",
    landmarksStatus: "Pyramids, Colosseum, Taj Mahal",
    daily: "Daily challenge",
    duel: "Duel",
    room: "Room",
    roomStatus: "With your friends, by code",
    soloStatus: (answerMode, rounds) =>
      `${answerMode} · ${String(rounds)} ${rounds === 1 ? "round" : "rounds"}`,

    unfinished: "You have an unfinished game",
    roundOf: (index, total) => `Round ${String(index)} of ${String(total)}`,
    resume: "Continue",
    replaceGame: (index, total) =>
      `The unfinished game (round ${String(index)} of ${String(total)}) will be dropped, and its points will not count. Start a new one?`,
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
