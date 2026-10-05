from app.tse import TSEClient

def test_parse_colon():
    t="CARG:6 TIPO:2 12345:87 NOMI:300 BRAN:2 NULO:1 TOTC:390"
    assert TSEClient.parse_imgbu(t,"12345")==87

def test_parse_space():
    t="CARG:6 TIPO:2 12345 54 NOMI:100"
    assert TSEClient.parse_imgbu(t,"12345")==54

def test_no_candidate():
    t="CARG:6 TIPO:2 99999:10 NOMI:100"
    assert TSEClient.parse_imgbu(t,"12345") is None
