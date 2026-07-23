FROM golang:1.23 AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /server ./cmd/server || true

FROM gcr.io/distroless/base
COPY --from=build /server /server
CMD ["/server"]
