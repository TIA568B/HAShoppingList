// Card-local manual collapse state, independent per shop and per category (Req 7.7).
// Never written back to the sensor. Composes with the server auto-collapse hint:
// - manual override (if the user has explicitly toggled) wins;
// - otherwise fall back to the server `collapsed` auto-collapse-when-empty hint.

export class CollapseState {
  constructor() {
    this._shops = new Map(); // shopName -> bool (manual collapsed)
    this._cats = new Map(); // `${shopName}\u0000${catName}` -> bool
  }

  _catKey(shop, cat) {
    return `${shop}\u0000${cat}`;
  }

  toggleShop(shop, autoHint = false) {
    const current = this._shops.has(shop) ? this._shops.get(shop) : autoHint;
    this._shops.set(shop, !current);
  }

  toggleCategory(shop, cat, autoHint = false) {
    const key = this._catKey(shop, cat);
    const current = this._cats.has(key) ? this._cats.get(key) : autoHint;
    this._cats.set(key, !current);
  }

  // Effective collapsed state: manual override if set, else the server auto hint.
  isShopCollapsed(shop, autoHint) {
    return this._shops.has(shop) ? this._shops.get(shop) : autoHint;
  }

  isCategoryCollapsed(shop, cat, autoHint) {
    const key = this._catKey(shop, cat);
    return this._cats.has(key) ? this._cats.get(key) : autoHint;
  }

  // Collapse every shop except the given one ("focus this shop").
  focusShop(focusShop, allShopNames) {
    for (const name of allShopNames) {
      this._shops.set(name, name !== focusShop);
    }
  }
}
