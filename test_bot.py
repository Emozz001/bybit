#!/usr/bin/env python3
"""
Test Suite for Unified Trading Bot
===================================
Run this script to verify the trading bot is properly configured and ready to use.

Usage:
    python3 test_bot.py

This test suite runs in simulation mode and does NOT execute real trades.
"""

import sys
import time
from datetime import datetime

def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_test(name, passed, message=""):
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status}: {name}")
    if message:
        print(f"       {message}")
    return passed

def main():
    print_header("UNIFIED TRADING BOT - TEST SUITE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_passed = True
    
    # Test 1: Module Import
    print_header("TEST 1: Module Import")
    try:
        from unified_trading_bot import (
            ArbConfig, TrendConfig, Position, Opportunity,
            TradeRecord, ArbTradeStats, TrendTradeStats,
            BybitArbBot, TrendTradingBot,
            ARB_CONFIG, TREND_CONFIG, LIVE_MODE, USE_TESTNET
        )
        all_passed &= print_test("Import all modules", True)
    except Exception as e:
        all_passed &= print_test("Import all modules", False, str(e))
        print("\n⚠️  CRITICAL: Cannot import modules. Please check dependencies.")
        print("   Run: pip install -r requirements.txt")
        return 1
    
    # Test 2: Configuration Loading
    print_header("TEST 2: Configuration Loading")
    try:
        arb_config = ArbConfig()
        all_passed &= print_test("ArbConfig created", True, 
            f"max_trade={arb_config.max_trade_amount_usdt} USDT, "
            f"min_profit={arb_config.min_profit_percent}%")
        
        trend_config = TrendConfig()
        all_passed &= print_test("TrendConfig created", True,
            f"symbol={trend_config.symbol}, timeframe={trend_config.timeframe}")
        
        all_passed &= print_test("Global configs available", True,
            f"LIVE_MODE={LIVE_MODE}, USE_TESTNET={USE_TESTNET}")
    except Exception as e:
        all_passed &= print_test("Configuration loading", False, str(e))
    
    # Test 3: Data Structures
    print_header("TEST 3: Data Structures")
    try:
        pos = Position.create(side='Buy', entry_price=50000, size=0.01,
                             stop_loss=49000, take_profit=52000)
        all_passed &= print_test("Position creation", True,
            f"{pos.side} @ {pos.entry_price} x{pos.size}")
        
        opp = Opportunity(symbol_a='BTC/USDT', symbol_b='ETH/BTC', path='USDT->BTC->ETH->USDT',
                         expected_profit_pct=0.5, price_a=50000, price_b=0.05, price_c=3000,
                         timestamp=time.time())
        all_passed &= print_test("Opportunity creation", True,
            f"profit={opp.expected_profit_pct}%")
        
        trade = TradeRecord(timestamp=time.time(), path='USDT->BTC->ETH->USDT', 
                           profit_pct=0.25, profit_usdt=0.12, status='success')
        all_passed &= print_test("TradeRecord creation", True,
            f"profit={trade.profit_usdt} USDT")
    except Exception as e:
        all_passed &= print_test("Data structures", False, str(e))
    
    # Test 4: Bot Instantiation
    print_header("TEST 4: Bot Instantiation")
    try:
        arb_bot = BybitArbBot()
        all_passed &= print_test("BybitArbBot created", True,
            f"LIVE_MODE={LIVE_MODE}")
        
        trend_bot = TrendTradingBot()
        all_passed &= print_test("TrendTradingBot created", True,
            f"test_mode={TREND_CONFIG.test_mode}")
    except Exception as e:
        all_passed &= print_test("Bot instantiation", False, str(e))
    
    # Test 5: Safety Features
    print_header("TEST 5: Safety Features")
    try:
        all_passed &= print_test("Simulation mode enabled", not LIVE_MODE,
            "Real trades are disabled by default")
        all_passed &= print_test("Testnet enabled", USE_TESTNET,
            "Using Bybit testnet for safety")
        all_passed &= print_test("Daily loss limit configured", 
            ARB_CONFIG.max_daily_loss_usdt > 0,
            f"max_daily_loss={ARB_CONFIG.max_daily_loss_usdt} USDT")
        all_passed &= print_test("Trade limits configured",
            ARB_CONFIG.max_daily_trades > 0,
            f"max_daily_trades={ARB_CONFIG.max_daily_trades}")
    except Exception as e:
        all_passed &= print_test("Safety features", False, str(e))
    
    # Summary
    print_header("TEST SUMMARY")
    if all_passed:
        print("✓ ALL TESTS PASSED!")
        print("\nThe trading bot is ready for testing in simulation mode.")
        print("\nNext steps:")
        print("  1. Get API keys from https://testnet.bybit.com/")
        print("  2. Update .env file with your API credentials")
        print("  3. Run: python3 unified_trading_bot.py")
        print("\n⚠️  WARNING: Always test in simulation mode before live trading!")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("\nPlease review the errors above and fix any issues.")
        print("Check that all dependencies are installed:")
        print("  pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())
