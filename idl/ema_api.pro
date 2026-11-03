; ema_api.pro -- minimal IDL helpers for the EMA PDC data-access API.
;
; Requires IDL 8.2 or later. Before use, set two environment variables:
;   EMA_DATA_ACCESS_URL  the API URL (required)
;   EMA_API_KEY          your API key (optional for queries and downloads;
;                        without it, only released files are visible.
;                        Uploading needs a developer-level key.)
;
; Compile once per IDL session with:  .compile ema_api
; See IDL.md for examples.


;+
; Read a text file into one string.
;
; Parameters
; ----------
; path : string
;   File to read.
;
; Returns
; -------
; string
;   The file's contents, or '' if it is missing or empty.
;-
function ema_read_text, path
  compile_opt idl2

  n = file_test(path) ? file_lines(path) : 0
  if n eq 0 then return, ''
  lines = strarr(n)
  openr, lun, path, /GET_LUN
  readf, lun, lines
  free_lun, lun
  return, strjoin(lines, string(10b))
end


;+
; Send one HTTP request and return the response.
;
; If the request fails, the error message includes the server's
; explanation (e.g. the coverage gaps for a metakernel request).
;
; Parameters
; ----------
; url : string
;   Full URL to request.
;
; Keywords
; --------
; API_KEY : string, optional
;   Sent as the x-api-key header. Omit for presigned S3 URLs.
; POST : string, optional
;   JSON body. If given, the request is a POST instead of a GET.
; PUT : string, optional
;   Path of a local file to send as an HTTP PUT, for presigned S3 upload
;   URLs.
; FILENAME : string, optional
;   Save the response to this file instead of returning it as text. The
;   file is only written if the request succeeds.
;
; Returns
; -------
; string
;   The response text, or FILENAME if FILENAME was given.
;-
function ema_http, url, API_KEY=api_key, POST=body, PUT=put_file, FILENAME=filename
  compile_opt idl2

  o = IDLnetURL()
  ; A bare 'Content-Type:' stops one being sent at all. Presigned S3 upload
  ; URLs aren't signed with a content type, so sending one makes S3 reject
  ; the upload.
  headers = n_elements(body) gt 0 ? ['Content-Type: application/json'] : ['Content-Type:']
  if keyword_set(api_key) then headers = [headers, 'x-api-key: ' + api_key]
  o->SetProperty, HEADERS=headers

  ; Every response goes to a scratch file first, so a failed request's
  ; error body can be read back and FILENAME is never left half-written.
  scratch = filepath('ema_response.tmp', /TMP)
  file_delete, scratch, /ALLOW_NONEXISTENT

  catch, err
  if err ne 0 then begin
    catch, /cancel
    o->GetProperty, RESPONSE_CODE=code
    obj_destroy, o
    detail = ema_read_text(scratch)
    message, 'EMA request failed (HTTP ' + strtrim(code, 2) + '): ' + url + $
      (detail ne '' ? string(10b) + detail : '')
  endif

  if n_elements(body) gt 0 then begin
    void = o->Put(body, /BUFFER, /POST, URL=url, FILENAME=scratch)
  endif else if n_elements(put_file) gt 0 then begin
    ; Without /BUFFER or /POST, Put sends the named file as an HTTP PUT.
    void = o->Put(put_file, URL=url, FILENAME=scratch)
  endif else begin
    void = o->Get(URL=url, FILENAME=scratch)
  endelse

  catch, /cancel
  obj_destroy, o

  if ~keyword_set(filename) then return, ema_read_text(scratch)
  file_move, scratch, filename, /OVERWRITE
  return, filename
end


;+
; Percent-encode a string for use as a URL query value.
;
; Without this, a '+' in a value (e.g. a '+00:00' time zone) reaches the
; server as a space, and an '&' splits the value into two parameters.
;
; Parameters
; ----------
; text : string
;   Value to encode.
;
; Returns
; -------
; string
;   TEXT with every character except A-Z a-z 0-9 - . _ ~ written as %XX.
;-
function ema_url_encode, text
  compile_opt idl2

  if strlen(text) eq 0 then return, ''
  out = ''
  foreach c, byte(text) do begin
    keep = (c ge 48b && c le 57b) || (c ge 65b && c le 90b) || $
      (c ge 97b && c le 122b) || c eq 45b || c eq 46b || c eq 95b || c eq 126b
    out += keep ? string(c) : '%' + string(c, FORMAT='(Z02)')
  endforeach
  return, out
end


;+
; Call a GET endpoint of the EMA API.
;
; Parameters
; ----------
; endpoint : string
;   Endpoint name, e.g. 'query_science' or 'metakernel'.
; params : hash, optional
;   Query parameters, e.g. hash('payload', 'embirs'). Write dates as
;   YYYY-MM-DD -- a bare 20240101 is read as seconds since 1970. Pass
;   SPICE times (seconds past J2000) as doubles: a float only holds about
;   7 digits, so a time near 9e8 can be off by a minute.
;
; Keywords
; --------
; TEXT : boolean, optional
;   Return the raw response text instead of parsing it as JSON.
;
; Returns
; -------
; list or string
;   For queries, a LIST of ORDEREDHASH rows; with /TEXT, the response text.
;-
function ema_query, endpoint, params, TEXT=text
  compile_opt idl2

  base = getenv('EMA_DATA_ACCESS_URL')
  if base eq '' then message, 'Set the EMA_DATA_ACCESS_URL environment variable.'

  query = ''
  if n_elements(params) gt 0 then foreach value, params, name do begin
    ; STRTRIM would print a float or double as e.g. 9.00000e+08, so write
    ; them out in full instead.
    type = size(value, /TYPE)
    value_text = (type eq 4 || type eq 5) ? string(value, FORMAT='(F0.6)') : strtrim(value, 2)
    query += (query eq '' ? '?' : '&') + name + '=' + ema_url_encode(value_text)
  endforeach

  response = ema_http(base + '/' + endpoint + query, API_KEY=getenv('EMA_API_KEY'))
  return, keyword_set(text) ? response : json_parse(response)
end


;+
; Download files from the EMA data archive by name.
;
; Parameters
; ----------
; file_names : string or string array
;   Exact names of the files to download.
; destination : string, optional
;   Directory to save the files in. Defaults to the current directory.
;-
pro ema_download, file_names, destination
  compile_opt idl2

  base = getenv('EMA_DATA_ACCESS_URL')
  if base eq '' then message, 'Set the EMA_DATA_ACCESS_URL environment variable.'
  dest = n_elements(destination) gt 0 ? destination : '.'
  file_mkdir, dest

  body = json_serialize(hash('filenames', list(file_names, /EXTRACT)))
  response = ema_http(base + '/download', API_KEY=getenv('EMA_API_KEY'), POST=body)

  foreach result, (json_parse(response))['results'] do begin
    if result['status_code'] ne 200 then begin
      print, 'Not downloaded: ' + result['filename'] + ' (' + result['detail'] + ')'
      continue
    endif
    ; Presigned URLs carry their own authorization, so no API key here.
    path = ema_http(result['download_url'], FILENAME=filepath(result['filename'], ROOT_DIR=dest))
    print, 'Downloaded ' + path
  endforeach
end


;+
; Upload a file, or every file in a directory, to the EMA data archive.
;
; File names must match a known EMA naming convention (see README.md), and
; EMA_API_KEY must be a developer-level key. Subdirectories and hidden
; files are skipped.
;
; Parameters
; ----------
; path : string
;   A file to upload, or a directory whose files are uploaded.
;-
pro ema_upload, path
  compile_opt idl2

  base = getenv('EMA_DATA_ACCESS_URL')
  if base eq '' then message, 'Set the EMA_DATA_ACCESS_URL environment variable.'

  if file_test(path, /DIRECTORY) then begin
    ; FILE_SEARCH skips hidden files unless /MATCH_INITIAL_DOT is set.
    ; With no matches FILE_SEARCH returns '' rather than nothing, so the
    ; result is only kept when COUNT says something was found.
    files = file_search(filepath('*', ROOT_DIR=path), COUNT=n)
    files = n gt 0 ? files[where(file_test(files, /REGULAR), /NULL)] : !NULL
  endif else if file_test(path, /REGULAR) then begin
    files = [path]
  endif else message, 'File not found: ' + path
  if n_elements(files) eq 0 then message, 'No files to upload in ' + path

  ; Map each bare file name back to its local path.
  local_paths = orderedhash(file_basename(files), files)

  body = json_serialize(hash('filenames', local_paths.keys()))
  response = ema_http(base + '/upload', API_KEY=getenv('EMA_API_KEY'), POST=body)

  foreach result, (json_parse(response))['results'] do begin
    if result['status_code'] ne 200 then begin
      print, 'Not uploaded: ' + result['filename'] + ' (' + result['detail'] + ')'
      continue
    endif
    ; Presigned URLs carry their own authorization, so no API key here.
    void = ema_http(result['upload_url'], PUT=local_paths[result['filename']])
    print, 'Uploaded ' + result['filename']
  endforeach
end
