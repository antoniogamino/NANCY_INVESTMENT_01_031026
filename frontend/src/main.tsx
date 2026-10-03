import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import "./index.css";
import Backtest from "./pages/Backtest";
import Dashboard from "./pages/Dashboard";
import DataSources from "./pages/DataSources";
import Performance from "./pages/Performance";
import Signals from "./pages/Signals";
import StockDetail from "./pages/StockDetail";
import Timeline from "./pages/Timeline";
import Trades from "./pages/Trades";
import Watchlist from "./pages/Watchlist";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/trades" element={<Trades />} />
          <Route path="/stock/:ticker" element={<StockDetail />} />
          <Route path="/timeline" element={<Timeline />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/performance" element={<Performance />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/watchlist" element={<Watchlist />} />
          <Route path="/data" element={<DataSources />} />
          <Route path="*" element={<div className="text-sm text-mute">Page not found.</div>} />
        </Routes>
      </Layout>
    </BrowserRouter>
  </React.StrictMode>,
);
