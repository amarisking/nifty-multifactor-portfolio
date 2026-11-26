# Career kit (fill the brackets with YOUR real results from results/REPORT.md)

## Resume bullets (pick 3-4)
- Built a Python framework for systematic Nifty 50 portfolio research: 5 factor signals, 5 portfolio construction methods (incl. Hierarchical Risk Parity, Ledoit-Wolf shrinkage), and a next-day-execution backtester with turnover-based costs.
- Implemented a risk layer (historical, parametric and GARCH-t VaR/CVaR backtested with the Kupiec test; volatility targeting; drawdown rules) that changed max drawdown from [X%] to [Y%].
- Validated results with walk-forward testing, parameter-sensitivity grids and block-bootstrap Sharpe intervals; found [one-line honest conclusion, e.g. "factor edge was not statistically distinguishable from the benchmark after costs"].
- Wrote unit tests that enforce no-lookahead and weight constraints; documented survivorship bias and other limitations.

## LinkedIn post template
I recently finished a course on algorithmic trading and portfolio management and wanted to test it on real data, so I built a research framework on the Nifty 50.

What I built: [one sentence]. 

What I found:
1. [Finding about factors vs benchmark]
2. [Finding about portfolio construction, e.g. HRP vs mean-variance]
3. [Finding about the risk overlay]

What did NOT work / what I'd distrust: [survivorship bias, one strategy that failed, wide bootstrap intervals].

Biggest lesson: [e.g. a good-looking backtest is the start of the questioning, not the end].

Code and full report: [GitHub link]

## Interview questions you must be able to answer
1. Why Ledoit-Wolf shrinkage? What goes wrong with the sample covariance matrix?
2. Why did you choose HRP before seeing results? What is data snooping?
3. How do you know there is no lookahead? (Point to the tests.)
4. What does a Kupiec p-value tell you? Why can GARCH-t VaR beat historical VaR?
5. Why is the bootstrap done in blocks?
6. What is survivorship bias and how large could it be here?
7. Why do walk-forward results usually look worse than the in-sample best?

## What-did-not-work section (write after running)
- Strategy / idea that failed and why:
- Parameter that turned out fragile:
- Result I decided not to trust, and why:
