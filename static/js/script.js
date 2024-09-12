document.addEventListener("DOMContentLoaded", function() {
    var chatWindow = document.querySelector('.chat-window');
    var newTaskButton = document.getElementById("newTaskButton"); // newTaskButton 변수 선언

    function scrollToBottom() {
        if (chatWindow) {
            var lastMessage = chatWindow.querySelector('.chat-message:last-child');
            if (lastMessage) {
                lastMessage.scrollIntoView({ behavior: 'smooth' });
            }
        }
    }

    if (chatWindow) {
        scrollToBottom(); // 페이지 로드 시 스크롤을 최하단으로 이동

        const observer = new MutationObserver(() => {
            scrollToBottom(); // DOM에 변동이 있을 때마다 스크롤을 최하단으로 이동
        });
        observer.observe(chatWindow, { childList: true, subtree: true });
    }

    var chatInputForm = document.querySelector(".chat-input-form");
    if (chatInputForm) {
        chatInputForm.addEventListener("submit", function(event) {
            event.preventDefault();

            var form = event.target;

            fetch(form.action, {
                method: 'POST',
                body: new FormData(form)
            })
            .then(response => response.text())
            .then(html => {
                document.querySelector('.container').innerHTML = html; // 서버에서 받은 응답으로 채팅창 업데이트
                form.reset();  // 폼 리셋
                scrollToBottom(); // 채팅창 스크롤을 하단으로 이동
            })
            .then(() => {
                window.location.reload();
                // 페이지를 새로고침하여 업데이트 확인
                if (chatWindow) {
                    chatWindow.scrollTop = chatWindow.scrollHeight; // 새로고침 후 스크롤을 최하단으로 이동
                }
            })
            .catch(error => console.error('Error during fetch:', error));
        });
    }

    function adjustLayout() {
        const isSidebarVisible = document.body.classList.contains('sidebar-visible');
        const chatContainer = document.querySelector('.container');
        const chatInputForm = document.querySelector('.chat-input-form');

        if (chatContainer && chatInputForm) {
            if (window.innerWidth >= 769) { // 웹에서
                if (isSidebarVisible) {
                    chatContainer.style.marginLeft = '200px';
                    chatContainer.style.width = 'calc(100% - 200px)';
                    chatInputForm.style.left = '200px';
                    chatInputForm.style.width = 'calc(100% - 200px)';
                } else {
                    chatContainer.style.marginLeft = '0';
                    chatContainer.style.width = '100%';
                    chatInputForm.style.left = '0';
                    chatInputForm.style.width = '100%';
                }
            } else { // 모바일에서
                chatContainer.style.marginLeft = '0';
                chatContainer.style.width = '100%';
                chatInputForm.style.left = '0';
                chatInputForm.style.width = '100%';
            }
        }
    }

    var sidebarToggle = document.querySelector('.sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            document.body.classList.toggle('sidebar-visible');
            document.body.classList.toggle('sidebar-hidden');
            adjustLayout(); // 레이아웃 조정
        });
    }

    adjustLayout();
    window.addEventListener('resize', adjustLayout);
    
    window.addEventListener("load", function() {
        setTimeout(scrollToBottom, 100);
    });

    document.querySelectorAll('.delete-history-btn').forEach(button => {
        button.addEventListener('click', function(event) {
            const summaryId = event.target.dataset.summaryId;
            if (confirm("이 대화 기록을 삭제하시겠습니까?")) {
                fetch(`/delete_summary/${summaryId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert("대화 기록이 삭제되었습니다.");
                        window.location.reload(); // 페이지 새로고침하여 UI 업데이트
                    } else {
                        alert("대화 기록 삭제에 실패했습니다.");
                    }
                })
                .catch(error => console.error('Error during deletion:', error));
            }
        });
    });

    if (newTaskButton) {
        newTaskButton.addEventListener("click", function() {
            fetch('/start_new_chat', {
                method: 'POST',
            })
            .then(response => response.json())
            .then(data => {
                console.log('Server response:', data);  // 서버 응답 로그 추가
                if (data.status === 'success') {
                    console.log('Summary ID:', data.summary_id);  // summary_id를 확인
                    if (data.summary_id) {
                        var summaryId = data.summary_id;  // 새로 생성된 summary_id
                        window.location.href = `/summary/${summaryId}`;  // 새로운 채팅으로 리디렉션
                    } else {
                        alert("서버 응답에 summary_id가 없습니다.");
                    }
                } else {
                    alert("새 채팅을 시작하는 데 실패했습니다.");
                }
            })
            
            .catch(error => {
                console.error('Error during new chat start:', error);
                alert("새 채팅 시작 중 오류가 발생했습니다.");
            });
        });
    }
    
    

    // 모달 창 관련 처리
    var closeButton = document.querySelector(".modal .close");
    console.log('Close Button:', closeButton); // 요소가 올바르게 선택되었는지 확인

    if (closeButton) {
        closeButton.addEventListener("click", function() {
            var modal = document.getElementById("successModal");
            if (modal) {
                modal.style.display = "none";
            }
        });
    }

    var redirectButton = document.getElementById("redirectToLogin");
    if (redirectButton) {
        redirectButton.addEventListener("click", function() {
            console.log("Redirect button clicked");
            window.location.href = "/login";
        });
    }

    if (document.body.classList.contains('modal-show')) {
        openModal();
    }

    function openModal() {
        var modal = document.getElementById("successModal");
        if (modal) {
            modal.style.display = "block";
        }
    }
        // 사용 가능한 색상 목록
        const colors = ['#FF5733', '#86E57F', '#6799FF', '#FF33A1', '#FF97FF', '#FFE08C', '#5CD1E5', '#CEF279'];

        // 이미 선택된 색상을 저장할 배열
        let usedColors = [];
    
        // 버튼 요소들을 가져오기
        const buttons = document.querySelectorAll('.chat-message.bot-message button');
    
        buttons.forEach(button => {
            let randomColor;
    
            if (usedColors.length >= colors.length) {
                usedColors = [];
            }
    
            // 색상이 겹치지 않도록 랜덤한 색상 선택
            do {
                randomColor = colors[Math.floor(Math.random() * colors.length)];
            } while (usedColors.includes(randomColor));
    
            // 선택된 색상을 저장
            usedColors.push(randomColor);
    
            // 버튼의 배경색을 랜덤하게 설정
            button.style.backgroundColor = randomColor;
    
            // hover 효과 설정
            button.addEventListener('mouseenter', function() {
                // 원래 색상보다 약간 어둡게 변경 (예시로 배경을 어둡게)
                button.style.backgroundColor = shadeColor(randomColor, -10);
            });
    
            button.addEventListener('mouseleave', function() {
                // 마우스가 버튼을 벗어나면 원래 색상 복원
                button.style.backgroundColor = randomColor;
            });
        });
    
        function shadeColor(color, percent) {
            let R = parseInt(color.substring(1,3),16);
            let G = parseInt(color.substring(3,5),16);
            let B = parseInt(color.substring(5,7),16);
    
            R = parseInt(R * (100 + percent) / 100);
            G = parseInt(G * (100 + percent) / 100);
            B = parseInt(B * (100 + percent) / 100);
    
            R = (R<255)?R:255;
            G = (G<255)?G:255;
            B = (B<255)?B:255;
    
            let RR = ((R.toString(16).length==1)?"0"+R.toString(16):R.toString(16));
            let GG = ((G.toString(16).length==1)?"0"+G.toString(16):G.toString(16));
            let BB = ((B.toString(16).length==1)?"0"+B.toString(16):B.toString(16));
    
            return "#"+RR+GG+BB;
        }
});
