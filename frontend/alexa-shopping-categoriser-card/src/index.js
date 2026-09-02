// Entry point: define the custom element and advertise it to the Lovelace card picker.

import { AlexaShoppingCategoriserCard } from "./card.js";

const TAG = "alexa-shopping-categoriser-card";

if (!customElements.get(TAG)) {
  customElements.define(TAG, AlexaShoppingCategoriserCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: TAG,
  name: "Alexa Shopping List Categoriser",
  description: "Shop-grouped, category-sorted view of your Alexa shopping list with tick and undo.",
});

// eslint-disable-next-line no-console
console.info("%c alexa-shopping-categoriser-card ", "color: white; background: #03a9f4;");
