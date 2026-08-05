BOARD_SIZE=10

board=[['.' for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

def show():
    print('   '+' '.join(f'{i}' for i in range(BOARD_SIZE)))
    for i,r in enumerate(board):
        print(f'{i:2} '+' '.join(r))

def win(x,y,s):
    for dx,dy in [(1,0),(0,1),(1,1),(1,-1)]:
        c=1
        for d in (1,-1):
            nx,ny=x,y
            while True:
                nx+=dx*d; ny+=dy*d
                if 0<=nx<BOARD_SIZE and 0<=ny<BOARD_SIZE and board[nx][ny]==s:c+=1
                else:break
        if c>=5:return True
    return False

p='X'
while True:
    show()
    try:x,y=map(int,input(f'{p} row col: ').split())
    except:continue
    if not(0<=x<BOARD_SIZE and 0<=y<BOARD_SIZE) or board[x][y]!='.':continue
    board[x][y]=p
    if win(x,y,p):show();print(p,'wins!');break
    p='O' if p=='X' else 'X'