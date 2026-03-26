export class State {
  constructor() {
    this.view = 'landing'; // 'landing', 'main', 'node', 'port'
    this.nodes = [];
    this.links = [];
    this.selectedNode = null;
    this.selectedPort = null;
    this.listeners = [];
  }

  subscribe(listener) {
    this.listeners.push(listener);
    // Initial call
    listener(this);
  }

  notify() {
    this.listeners.forEach(l => l(this));
  }

  setState(updates) {
    Object.assign(this, updates);
    this.notify();
  }
}

export const appState = new State();
