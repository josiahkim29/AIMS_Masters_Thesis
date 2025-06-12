# AIMS Master's Thesis

This is the GitHub repository for my Master's Thesis in partial fulfilment for the award of MSc. Mathematical Sciences(AI for Sciences) from the African Institute for Mathematical Sciences(AIMS)-South Africa, accredited by Stellenbosch University.

**Title:** 

**PiggyCast: Improving Weather Prediction Accuracy through a Stacking-Based Ensemble AI Approach**

**Abstract**:

Recently, AI Weather Prediction (AIWP) models have outperformed classical Numerical Models in various weather prediction benchmarking criteria. Given the paradigm shift from numerical to machine learning models, such forecasts can be generated in seconds to minutes on a standard laptop. Forecast
datasets from frontier AIWP models for the year 2020 have been made publicly available on the WeatherBench 2 website, facilitating independent analysis, evaluation, and further research. In this study, we introduce a traditional machine learning model trained on top of these forecast datasets (a method known as “stacking”) to predict ERA5 variables, thereby exploiting the strengths of each base model and aiming to outperform forecasts from any base model alone. We coin our model ’**PiggyCast**’, as we effectively piggyback off the work done by leading AI research teams with expertise and compute budgets for model training that are hard to match in an MSc thesis. The improvement in PiggyCast’s Root Mean Squared Error on Geopotential Height at 500 hPa pressure, relative to the base models, was notable, with an increase in performance as forecast lead time increased. Given the low compute cost of making forecasts, and that each frontier AIWP model has its strengths and weaknesses (depending on the weather variable, region of the globe, and forecast lead time), we argue that the future of the most skilful weather forecasts will likely come from machine learning stacking, by the very nature that stacking typically yields performance better than any base model alone.


**Project Outline**

AIMS_Masters_Thesis/

├── Notebooks/                  
│   ├── DataPrep/

│   ├── PiggyCast/ 

│   ├── Unsupervised Learning/

├── Plots/            
├── Report/                 
└── README.md                # This file
