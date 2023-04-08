import React, { useState }from 'react'
import { Link } from 'react-router-dom'
import "../css/login.css"
import "../css/grid.min.css"

const Login=()=>{
    const [inputId, setInputId] = useState('')
    const [inputPw, setInputPw] = useState('')

    const handleInputId = (e) => {
        setInputId(e.target.value)
    }
    const handleInputPw = (e) => {
        setInputPw(e.target.value)
    }

    const onClickLogin = () => {
        console.log('click login')
    }

    return (
        <>
        <div className="container">
            <div className="login_page">
                <div className="login_title">
                    <div className="row">
                        <div className="col-12">
                            <h1>물어봇</h1>
                        </div>
                    </div>
                </div>

                <div className="input_group">
                    <div className="row">
                        <div className="col-12">
                            <input className="input_id" type='text' name='input_id' placeholder="아이디를 입력하세요" value={inputId} onChange={handleInputId}/>
                        </div>
                    </div>
                    <div className="row">
                        <div className="col-12">
                            <input className="input_pw" type='password' name='input_pw' placeholder="비밀번호를 입력하세요"value={inputPw} onChange={handleInputPw}/>

                        </div>
                    </div>
                </div>

                <div className="login_button">
                    <div className="row">
                        <div className="col-12">
                            <Link to="/Chat">
                                <div>
                                    <button type='button' onClick={onClickLogin}>Login</button>
                                </div>
                            </Link>
                        </div>
                    </div>
                </div>
                
                
                <div className="goto_signup_div">
                    <div className="row">
                        <div className="col-7"></div>
                        <div className="col-3">
                            <div>
                                <Link className="goto_signup" to="/SignUp">회원가입</Link>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            
        </div>
        
        </>
    )
}

export default Login;