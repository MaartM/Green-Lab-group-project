# Hourly carbon intensity of the Dutch electricity mix from the Nationaal Energie Dashboard
# (NED, https://ned.nl), and its match to the runs. 

NED_API <- "https://api.ned.nl/v1/utilizations"
NED_PAGE_SIZE <- 200

# One page of hourly electricity mix values for the Netherlands, in UTC, as a data frame.
ned_page <- function(from_date, to_date, page) {
  query <- c(point = 0,                  # the Netherlands
             type = 27,                  # electricity mix
             granularity = 5,            # hour
             granularitytimezone = 0,    # UTC
             classification = 2,         # measured, not forecast
             activity = 1,               # providing
             "validfrom[after]" = from_date, "validfrom[strictly_before]" = to_date,
             itemsPerPage = NED_PAGE_SIZE, page = page)
  request <- paste0(NED_API, "?", paste(names(query), query, sep = "=", collapse = "&"))
  file <- tempfile(fileext = ".csv")
  on.exit(unlink(file))
  status <- tryCatch(
    download.file(request, file, method = "libcurl", quiet = TRUE,
                  headers = c("X-AUTH-TOKEN" = Sys.getenv("NED_API_KEY"), Accept = "text/csv")),
    error = function(e) stop("NED request failed (", conditionMessage(e), "); check NED_API_KEY")
  )
  if (status != 0 || file.size(file) == 0) return(data.frame())
  read.csv(file, stringsAsFactors = FALSE)
}

fetch_grid_intensity <- function(from, to) {
  if (Sys.getenv("NED_API_KEY") == "") {
    stop("no cached grid intensity for ", EXPERIMENT, " and NED_API_KEY is not set; see analysis/grid_intensity.R")
  }
  # NED filters by date, so fetch whole days and keep every hour.
  from_date <- format(from, "%Y-%m-%d", tz = "UTC")
  to_date <- format(to + 86400, "%Y-%m-%d", tz = "UTC")
  pages <- list()
  repeat {
    page <- ned_page(from_date, to_date, length(pages) + 1)
    pages[[length(pages) + 1]] <- page
    if (nrow(page) < NED_PAGE_SIZE) break
  }
  values <- do.call(rbind, pages)
  if (!nrow(values)) stop("NED returned no electricity mix values between ", from_date, " and ", to_date)
  hour <- function(x) as.POSIXct(substr(x, 1, 19), format = "%Y-%m-%dT%H:%M:%S", tz = "UTC")
  data.frame(valid_from = format(hour(values$validfrom), "%Y-%m-%dT%H:%M:%SZ"),
             valid_to = format(hour(values$validto), "%Y-%m-%dT%H:%M:%SZ"),
             emission_factor_kg_per_kwh = as.numeric(values$emissionfactor),
             volume_kwh = as.numeric(values$volume),
             emission_kg = as.numeric(values$emission),
             last_update = values$lastupdate,
             fetched = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"))
}

# Cached hourly values covering [from, to], fetched from NED if not cached yet.
grid_intensity <- function(from, to) {
  cache <- file.path(GRID_INTENSITY_DIR, paste0(EXPERIMENT, ".csv"))
  if (!file.exists(cache)) {
    dir.create(GRID_INTENSITY_DIR, recursive = TRUE, showWarnings = FALSE)
    write.csv(fetch_grid_intensity(from, to), cache, row.names = FALSE)
    cat("fetched grid intensity from NED into", cache, "\n")
  }
  hours <- read.csv(cache, stringsAsFactors = FALSE)
  for (column in c("valid_from", "valid_to")) {
    hours[[column]] <- as.POSIXct(hours[[column]], format = "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
  }
  hours[order(hours$valid_from), ]
}

run_intensity <- function(start, duration_s, hours) {
  mapply(function(start, duration_s) {
    end <- start + duration_s
    overlap_s <- pmax(0, as.numeric(pmin(end, hours$valid_to)) - as.numeric(pmax(start, hours$valid_from)))
    if (abs(sum(overlap_s) - duration_s) > 1) stop("grid intensity does not cover the run starting ", start)
    1000 * sum(overlap_s * hours$emission_factor_kg_per_kwh) / sum(overlap_s)
  }, start, duration_s)
}
